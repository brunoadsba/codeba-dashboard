def levenshtein_distance(s1, s2):
    """Calcula a distância de Levenshtein entre duas strings (suporta inserção, deleção e substituição)."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _is_valid_mercosul_format(placa: str) -> bool:
    """Verifica se a placa segue o formato Mercosul (ABC1D23 ou ABC1234)."""
    if len(placa) != 7:
        return False
    # Padrão antigo: ABC1234 (3 letras + 4 números)
    if placa[:3].isalpha() and placa[3:].isdigit():
        return True
    # Padrão Mercosul: ABC1D23 (3 letras + 1 dígito + 1 letra + 2 dígitos)
    if (placa[:3].isalpha() and placa[3].isdigit() and
        placa[4].isalpha() and placa[5:].isdigit()):
        return True
    return False


def detect_plate_typos(divergencias):
    """
    Pós-processamento: identifica pares de divergências (Falta no PDF + Falta no Excel)
    que na verdade são erros de digitação da placa (mesma data, mesmos pesos, placa similar).

    A detecção é bidirecional: identifica qual das duas placas (Excel ou PDF) está no formato
    correto de placa Mercosul para determinar a direção do erro.
    """
    def _safe_float(val, default=0.0):
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    falta_pdf = [(i, d) for i, d in enumerate(divergencias) if d.get('Status') == 'Falta no PDF']
    falta_excel = [(i, d) for i, d in enumerate(divergencias) if d.get('Status') == 'Falta no Excel']

    indices_to_remove = set()
    typo_entries = []
    used_excel = set()

    TOLERANCIA_TYPO_KG = 50

    for i_fp, fp in falta_pdf:
        for i_fe, fe in falta_excel:
            if i_fe in used_excel:
                continue
            # Comparar apenas a data (desprezando hora)
            if (fp.get('Data', '') or '').split(' ')[0] != (fe.get('Data', '') or '').split(' ')[0]:
                continue
            # Comparar pesos
            if (abs(_safe_float(fp.get('Peso Bruto')) - _safe_float(fe.get('Peso Bruto'))) < TOLERANCIA_TYPO_KG and
                abs(_safe_float(fp.get('Tara')) - _safe_float(fe.get('Tara'))) < TOLERANCIA_TYPO_KG):
                dist = levenshtein_distance(fp.get('Placa', ''), fe.get('Placa', ''))
                if 1 <= dist <= 2:
                    used_excel.add(i_fe)
                    indices_to_remove.add(i_fp)
                    indices_to_remove.add(i_fe)

                    # Determinar direção do erro: a placa em formato Mercosul válido é a correta
                    placa_excel = fp.get('Placa', '')
                    placa_pdf = fe.get('Placa', '')
                    placa_corrigida = placa_pdf if _is_valid_mercosul_format(placa_pdf) else placa_excel
                    placa_digitada_errado = placa_excel if placa_corrigida == placa_pdf else placa_pdf

                    typo_entries.append({
                        'Placa': placa_corrigida,
                        'Placa_Excel': placa_excel,
                        'Placa_PDF': placa_pdf,
                        'Data': fe.get('Data', ''),
                        'Status': 'Erro de Placa',
                        'Detalhe': f"Placa '{placa_digitada_errado}' não confere. Corrigida para '{placa_corrigida}'.",
                        'Produto': fp.get('Produto', ''),
                        'Cliente': fp.get('Cliente', ''),
                        'Peso Bruto': _safe_float(fp.get('Peso Bruto')),
                        'Tara': _safe_float(fp.get('Tara')),
                        'Peso Liquido': _safe_float(fp.get('Peso Bruto')) - _safe_float(fp.get('Tara')),
                        'Motivacao': fp.get('Motivacao', '') or fe.get('Motivacao', ''),
                        'SEV': fe.get('SEV', '')
                    })
                    break

    # Reconstruir lista sem os índices removidos, adicionando os typos
    result = [d for i, d in enumerate(divergencias) if i not in indices_to_remove]
    result.extend(typo_entries)
    return result


def infer_product_from_history(ok_list, divergencias):
    """
    Para divergências do tipo 'Falta no Excel', tenta deduzir o produto
    baseando-se no histórico de viagens OK da mesma placa.
    """
    # Construir mapa: placa -> set de produtos observados nos registros OK
    placa_produtos = {}
    for item in ok_list:
        placa = item.get('Placa', '')
        produto = item.get('Produto', '')
        if placa and produto:
            if placa not in placa_produtos:
                placa_produtos[placa] = set()
            placa_produtos[placa].add(produto)

    # Também considerar divergências que já têm produto (Falta no PDF, Diferença de Peso)
    for item in divergencias:
        placa = item.get('Placa', '')
        produto = item.get('Produto', '')
        if placa and produto and item.get('Status') not in ('Falta no Excel',):
            if placa not in placa_produtos:
                placa_produtos[placa] = set()
            placa_produtos[placa].add(produto)

    # Aplicar dedução
    for item in divergencias:
        if item.get('Status') == 'Falta no Excel' and not item.get('Produto'):
            placa = item.get('Placa', '')
            if placa in placa_produtos:
                produtos = placa_produtos[placa]
                if len(produtos) == 1:
                    item['Produto'] = f"{list(produtos)[0]} (Deduzido)"
                else:
                    item['Produto'] = f"Ambíguo ({', '.join(sorted(produtos))})"
            else:
                item['Produto'] = 'Não Identificado'

    return divergencias
