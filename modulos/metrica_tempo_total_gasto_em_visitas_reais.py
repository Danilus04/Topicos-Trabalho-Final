import json
from datetime import datetime

def calcular_tempo_total_gasto_em_visitas_reais(statements, caminho_arquivo_saida="resultado_tempo_total_gasto_em_visitas_reais.json", timeout_minutos=600):
    # Transforma o timeout para segundos
    timeout_segundos = timeout_minutos * 60 if timeout_minutos > 0 else float('inf')

    # Ordena statements por timestamp (garante ordem cronológica)
    statements.sort(key=lambda s: s.get("timestamp", ""))

    # Agrupa por usuário
    usuarios_statements = {}
    for statement in statements:
        actor = statement.get("actor", {}).get("account", {}).get("name")
        if not actor:
            continue
        usuarios_statements.setdefault(actor, []).append(statement)

    resultado = []

    for usuario, stmts in usuarios_statements.items():
        sessao_inicio = None
        ultima_atividade = None

        for statement in stmts:
            timestamp_str = statement.get("timestamp")
            if not timestamp_str:
                continue
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            verb_display = statement.get("verb", {}).get("display", {}).get("en", "").strip().lower()

            # 1. INÍCIO FANTASMA: Se não tem sessão aberta, abre uma agora.
            if sessao_inicio is None:
                sessao_inicio = ts
                ultima_atividade = ts

            # Calcula o tempo desde o último clique
            tempo_ocioso = (ts - ultima_atividade).total_seconds()

            # 2. REGRAS DE CORTE DE SESSÃO:
            # Cortamos a sessão SE: for um novo login, OU se estourou o tempo de inatividade
            if verb_display == "logged in" or tempo_ocioso > timeout_segundos:
                
                # Só salva se a sessão durou mais que 0 segundos (evita lixo no dataset)
                diff_seconds = int((ultima_atividade - sessao_inicio).total_seconds())
                if diff_seconds > 0:
                    resultado.append({
                        "usuario": usuario,
                        "timestamp_login": sessao_inicio.isoformat(),
                        "timestamp_atividade": ultima_atividade.isoformat(),
                        "tempo_passado_segundos": diff_seconds, # Útil ter em int para facilitar gráficos depois
                        "tempo_passado": f"PT{diff_seconds}S"
                    })

                # Inicia a próxima sessão a partir deste evento atual
                sessao_inicio = ts
                ultima_atividade = ts

            # 3. REGRA DO LOGOUT EXPLICITO
            elif verb_display == "logged out":
                diff_seconds = int((ts - sessao_inicio).total_seconds())
                if diff_seconds > 0:
                    resultado.append({
                        "usuario": usuario,
                        "timestamp_login": sessao_inicio.isoformat(),
                        "timestamp_atividade": ts.isoformat(),
                        "tempo_passado_segundos": diff_seconds,
                        "tempo_passado": f"PT{diff_seconds}S"
                    })
                # Zera as variáveis, a próxima linha do loop forçará um Início Fantasma
                sessao_inicio = None
                ultima_atividade = None

            # 4. COMPORTAMENTO PADRÃO: Só atualiza o ponteiro de última atividade
            else:
                ultima_atividade = ts

        # Fechamento de segurança: Salva qualquer sessão que tenha ficado aberta no final do loop
        if sessao_inicio is not None and ultima_atividade is not None:
            diff_seconds = int((ultima_atividade - sessao_inicio).total_seconds())
            if diff_seconds > 0:
                resultado.append({
                    "usuario": usuario,
                    "timestamp_login": sessao_inicio.isoformat(),
                    "timestamp_atividade": ultima_atividade.isoformat(),
                    "tempo_passado_segundos": diff_seconds,
                    "tempo_passado": f"PT{diff_seconds}S"
                })

    # Salva em JSON
    with open(caminho_arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    return resultado