import json, sys
d = json.load(sys.stdin)
print(f"OK: {d['resumo']['ok']}  DIV: {d['resumo']['divergencias']}")
print(f"Produtos: {d.get('produtos_detectados', [])}")
print(f"Clientes: {d.get('clientes_por_produto', {})}")
for x in d.get('divergencias', []):
    print(f"  DIV: {x['Placa']} | {x['Status']} | Prod: {x.get('Produto', '')}")
for x in d.get('ok', [])[:3]:
    print(f"  OK: {x['Placa']} | Prod: {x.get('Produto', '')} | PL: {x.get('Peso Liquido', 'N/A')}")
