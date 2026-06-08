import os
import argparse
from datetime import datetime
from playwright.sync_api import sync_playwright

def run_rpa(data_inicio, data_fim, download_dir):
    with sync_playwright() as p:
        # headless=False mostra o navegador na tela durante os testes. 
        # Quando quiser rodar invisível, mude para headless=True
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()

        try:
            print("1. Acessando a página de login...")
            page.goto("https://openportilheus.codeba.gov.br/openportcodeba/")

            print("2. Realizando login (simulando digitação humana)...")
            page.locator("xpath=/html/body/div/div[2]/form/div[1]/div/input").press_sequentially("01879832593", delay=120)
            page.locator("xpath=/html/body/div/div[2]/form/div[2]/div/input").press_sequentially("#@Codeba2030", delay=120)
            page.wait_for_timeout(500) # Pausa rápida antes de clicar
            page.locator("xpath=/html/body/div/div[2]/form/div[4]/div[2]/div/button").click()

            print("3. Pesquisando pela tela 7015...")
            # Digitar na barra de pesquisa tecla por tecla
            page.locator("xpath=/html/body/div/div[1]/div/div[3]/form/div/span[1]/input[2]").press_sequentially("7015", delay=150)
            # Clicar na Lupa
            page.locator("xpath=/html/body/div/div[1]/div/div[3]/form/div/span[2]/button/i").click()
            
            # Pausa rápida para a tela/menu carregar
            page.wait_for_timeout(2000)
            
            # Clicar na opção 7015 listada
            page.locator("xpath=/html/body/div[3]/form/fieldset/div[2]/ul/li/div/label").click()

            print(f"4. Preenchendo período: {data_inicio} até {data_fim}")
            page.locator("xpath=/html/body/div[3]/form/fieldset/div[1]/div[3]/div/div/input[1]").press_sequentially(data_inicio, delay=100)
            page.wait_for_timeout(300)
            page.locator("xpath=/html/body/div[3]/form/fieldset/div[1]/div[3]/div/div/input[2]").press_sequentially(data_fim, delay=100)

            print("5. Filtrando e gerando o relatório...")
            page.locator("xpath=/html/body/div[3]/div[1]/button[2]").click()

            # Botão imprimir da aplicação
            print("6. Preparando tela de impressão...")
            page.locator("xpath=/html/body/div[3]/div[1]/button[5]").click()

            # Aguardar 5 segundos para o relatório renderizar completamente na tela
            page.wait_for_timeout(5000) 

            # Montar o nome do arquivo
            nome_arquivo = f"{data_inicio.replace('/', '_')}_a_{data_fim.replace('/', '_')}.pdf"
            caminho_completo = os.path.join(download_dir, nome_arquivo)

            print(f"7. Gerando PDF internamente e salvando em: {caminho_completo}")
            # Comando "secreto": Salva a tela atual em PDF nativamente, sem usar o Ctrl+P do Windows
            # format="A4", landscape=True deita a folha para caber melhor relatórios largos
            page.pdf(path=caminho_completo, format="A4", landscape=True, print_background=True)

            print("✅ Sucesso! PDF salvo com êxito.")

        except Exception as e:
            print(f"❌ Ocorreu um erro durante a automação: {e}")
        
        finally:
            # Sempre fecha o navegador no final, mesmo se der erro
            browser.close()

if __name__ == "__main__":
    # Minha recomendação para datas dinâmicas:
    # O script aceita que as datas sejam digitadas manualmente no terminal,
    # OU oferece uma opção rápida de "Mês Atual", perfeita para o dia-a-dia.
    
    print("="*40)
    print("RPA CODEBA - EXTRAÇÃO RELATÓRIO 7015")
    print("="*40)
    
    resposta = input("Deseja rodar com as datas do MÊS ATUAL? (S/N): ").strip().upper()
    
    hoje = datetime.now()
    if resposta == 'S':
        # Calcula do dia 01 do mês atual até o dia de hoje
        primeiro_dia = hoje.replace(day=1)
        data_inicio = primeiro_dia.strftime("%d/%m/%Y")
        data_fim = hoje.strftime("%d/%m/%Y")
    else:
        # Pede para digitar se for 'N'
        data_inicio = input("Digite a data de Início (ex: 13/05/2026): ").strip()
        data_fim = input("Digite a data de Fim (ex: 02/06/2026): ").strip()
        
    download_dir = r"C:\Users\bruno.santos\Downloads\Projetos"
    
    print(f"\nIniciando robô para o período {data_inicio} até {data_fim}...")
    run_rpa(data_inicio, data_fim, download_dir)
