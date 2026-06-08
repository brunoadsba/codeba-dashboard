def plate_char_diff(placa1, placa2):
    """Conta diferenças caractere a caractere entre duas placas de mesmo tamanho."""
    if len(placa1) != len(placa2):
        return max(len(placa1), len(placa2))
    return sum(c1 != c2 for c1, c2 in zip(placa1, placa2))


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
            if fp['Data'] != fe['Data']:
                continue
            # Comparar pesos
            if abs(fp['Peso Bruto'] - fe['Peso Bruto']) < 0.1 and abs(fp['Tara'] - fe['Tara']) < 0.1:
                dist = plate_char_diff(fp['Placa'], fe['Placa'])
                if 1 <= dist <= 2:
                    used_excel.add(i_fe)
                    indices_to_remove.add(i_fp)
                    indices_to_remove.add(i_fe)
                    typo_entries.append({
                        'Placa': fp['Placa'],
                        'Placa_Excel': fp['Placa'],
                        'Placa_PDF': fe['Placa'],
                        'Data': fp['Data'],
                        'Status': 'Erro de Placa',
                        'Detalhe': f"Placa digitada '{fp['Placa']}' no Excel, mas registrada como '{fe['Placa']}' no OpenPort. Pesos idênticos: Bruto {fp['Peso Bruto']}kg / Tara {fp['Tara']}kg.",
                        'Produto': fp.get('Produto', ''),
                        'Cliente': fp.get('Cliente', ''),
                        'Peso Bruto': fp['Peso Bruto'],
                        'Tara': fp['Tara'],
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
