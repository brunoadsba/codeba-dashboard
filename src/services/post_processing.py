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


def detect_plate_typos(divergencias):
    """
    Pós-processamento: identifica pares de divergências (Falta no PDF + Falta no Excel)
    que na verdade são erros de digitação da placa (mesma data, mesmos pesos, placa similar).
    """
    falta_pdf = [(i, d) for i, d in enumerate(divergencias) if d['Status'] == 'Falta no PDF']
    falta_excel = [(i, d) for i, d in enumerate(divergencias) if d['Status'] == 'Falta no Excel']
    
    indices_to_remove = set()
    typo_entries = []
    used_excel = set()
    
    for i_fp, fp in falta_pdf:
        for i_fe, fe in falta_excel:
            if i_fe in used_excel:
                continue
            # Comparar apenas a data (desprezando hora)
            if fp['Data'].split(' ')[0] != fe['Data'].split(' ')[0]:
                continue
            # Comparar pesos
            if abs(fp['Peso Bruto'] - fe['Peso Bruto']) < 0.1 and abs(fp['Tara'] - fe['Tara']) < 0.1:
                dist = levenshtein_distance(fp['Placa'], fe['Placa'])
                if 1 <= dist <= 2:
                    used_excel.add(i_fe)
                    indices_to_remove.add(i_fp)
                    indices_to_remove.add(i_fe)
                    typo_entries.append({
                        'Placa': fp['Placa'],
                        'Placa_Excel': fp['Placa'],
                        'Placa_PDF': fe['Placa'],
                        'Data': fe['Data'],  # Utiliza a data/hora exata do PDF
                        'Status': 'Erro de Placa',
                        'Detalhe': f"Placa digitada '{fp['Placa']}' no Excel, mas registrada como '{fe['Placa']}' no OpenPort. Pesos idênticos: Bruto {fp['Peso Bruto']}kg / Tara {fp['Tara']}kg.",
                        'Produto': fp.get('Produto', ''),
                        'Cliente': fp.get('Cliente', ''),
                        'Peso Bruto': fp['Peso Bruto'],
                        'Tara': fp['Tara'],
                        'PR': fp.get('PR', '') or fe.get('PR', ''),
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
        if placa and produto and item['Status'] not in ('Falta no Excel',):
            if placa not in placa_produtos:
                placa_produtos[placa] = set()
            placa_produtos[placa].add(produto)
    
    # Aplicar dedução
    for item in divergencias:
        if item['Status'] == 'Falta no Excel' and not item.get('Produto'):
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
