#!/usr/bin/env python
# coding: utf-8

#Bibliotecas
import json
from urllib.parse import urlencode
import os
import io
from datetime import datetime
from datetime import timedelta
import requests
import pandas as pd
from pypdf import PdfReader
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb


# sigen_authenticate: Função que loga no sistema Sigen+
def sigen_authenticate(user, password):
    output = {
        'user': user,
        'session': None,
        'status_code': None,
        'login_error': False,
        'error_message': None
    }

    url = "https://sigen.cidasc.sc.gov.br/Account/Login"
    payload = {
        "nmUsuario": user,
        "dsSenha": password,
        "dsBrowser": "Chrome",
        "dsVersion": "136"
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Origin": "https://sigen.cidasc.sc.gov.br",
        "Referer": "https://sigen.cidasc.sc.gov.br/Account/LogOn"
    }

    session = requests.Session()
    try:
        response = session.post(url, headers=headers, data=json.dumps(payload))
        output['status_code'] = response.status_code

        if response.status_code == 200 and 'redirectUrl' in response.json():
            output['session'] = session
        else:
            output['login_error'] = True
            output['error_message'] = response.json().get("ErrorMessage", "Erro desconhecido")
            session.close()

    except Exception as e:
        output['login_error'] = True
        output['error_message'] = str(e)
        session.close()

    return output



# get_ueps: Função para obter a lista de ueps de um código oficial
def get_ueps(cd_oficial,session):
    output = {
        "ueps": None,
        'errors':{
        "response_error": False,
        "parsing_error": False,
        "data_error": False,
        "error_message": ""
        }
    }

    post_data = {
        "filtroDataSaida": "",
        "fitroHabilitacao": "false",
        "flTek": "false",
        "filtroEvento": "false",
        "listarExcluidas": "true",
        "listarSituacao": "true",
        "listarTodas": "false",
        "filtroForaDoEstado": "N",
        "idPessoaAutorizada": "0",
        "listarProdutor": "false",
        "id_unidade_exploracao": "",
        "cd_oficial_propriedade": cd_oficial,
        "nr_unidade_exploracao": "",
        "flUep": "true",
        "ds_flag_Value": "",
        "ds_flag": "",
        "ext-comp-1075_SelIndex": "",
        "cs_situacao_propriedade_Value": "AT",
        "cs_situacao_propriedade": "Ativa",
        "ext-comp-1076_SelIndex": "1",
        "cb_responsavel_Value": "",
        "cb_responsavel": "Documento (CPF/CNPJ) ou Nome e Município",
        "cb_responsavel_SelIndex": "",
        "cb_Produtor_Value": "",
        "cb_Produtor": "",
        "cb_Produtor_SelIndex": "",
        "cb_Evento_Value": "",
        "cb_Evento": "",
        "cb_Evento_SelIndex": "",
        "cb_especie_animal_Value": "1",
        "cb_especie_animal": "BOVINO",
        "searchUepEspecie_SelIndex": "-1",
        "cb_Localidade_Value": "",
        "cb_Localidade": "",
        "cb_Localidade_SelIndex": "",
        "cb_Municipio_Value": "",
        "cb_Municipio": "",
        "cb_Municipio_SelIndex": "",
        "cb_finalidade_criacao_Value": "",
        "cb_finalidade_criacao": "",
        "searchUepFinalidade_SelIndex": "-1"
    }

    url = "https://sigen.cidasc.sc.gov.br/DSA.Cadastros/UnidadeExploracao/PerformSearch"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = session.post(url=url, headers=headers, data=urlencode(post_data))

        if response.status_code != 200:
            output['errors']["response_error"] = True
            output['errors']["error_message"] = f"Erro na requisição: {response.status_code}"
            return output
        if "<title>SIGEN+" in response.text and "formLogin" in response.text:
            output['errors']["response_error"] = True
            output['errors']["error_message"] = "Usuário não logado"
            return output
        try:
            json_data = response.json()

            if not json_data.get("success", False):
                output['errors']["parsing_error"] = True
                output['errors']["error_message"] = json_data.get("ErrorMessage", "Resposta sem sucesso.")
                return output

            data = json_data.get("data", [])
            ueps_ids = [item.get("id_unidade_exploracao") for item in data]
            if not ueps_ids:
                output['errors']["data_error"] = True
                output['errors']["error_message"] = "Nenhuma unidade de exploração encontrada."
                return output
            output["ueps"] = ueps_ids

        except Exception as e:
            output['errors']["parsing_error"] = True
            output['errors']["error_message"] = f"Erro ao interpretar resposta JSON: {str(e)}"

    except Exception as e:
        output['errors']["response_error"] = True
        output['errors']["error_message"] = f"Erro de requisição: {str(e)}"

    return output



# Uso
#session = session (teste global)
# cd_oficial = 31317
# resultado = get_ueps(cd_oficial,session)



# if resultado['errors']["response_error"] == True:
#     print('response error '+ resultado['errors']['error_message'])
#     if resultado['errors']["parsing_error"] == True:
#         print('parsing error '+ resultado['errors']['error_message'])
#         if resultado['errors']["data_error"] == True:
#             print('data error '+ resultado['errors']['error_message'])
# else:
#     display(resultado["ueps"])  





# get_atRebanho: função para gerar uma arrow table a partir dos pdfs das unidades de exploração
def get_atRebanho(ueps, date,session):
    output = {
        "atRebanho": None,
        'errors':{
        "response_error": False,
        "parsing_error": False,
        "data_error": False,
        "error_message": ""
        }
    }

    url = "https://sigen.cidasc.sc.gov.br/DSA.Cadastros/UnidadeExploracao/ImprimeInventarioAnimais"

    all_registers = []

    try:
        for idUnidadeExploracao in ueps:
            payload = {
                'idUnidadeExploracao': str(idUnidadeExploracao),
                'dtConsulta': date
            }

            try:
                response = session.post(url, data=payload)
                response.raise_for_status()
                if "<title>SIGEN+" in response.text and "formLogin" in response.text:
                        output['errors']["response_error"] = True
                        output['errors']["error_message"] = "Usuário não logado"
                        return output
            except Exception as e:
                output['errors']["response_error"] = True
                output['errors']["error_message"] = f"Erro na requisição da UEP {idUnidadeExploracao}: {str(e)}"
                return output

            try:
                reader = PdfReader(io.BytesIO(response.content))
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

                start = full_text.find("Estratificação")
                if start == -1:
                    continue

                end = full_text.find(" Brincos em Trânsito para Propriedade", start)
                if end == -1:
                    end = full_text.find("Total Geral", start)
                    if end == -1:
                        end = len(full_text)

                table_text = full_text[start:end]
                rows = table_text.strip().split("\n")

                # Remove cabeçalhos
                while rows and (
                    "Nº Brinco" in rows[0]
                    or "Espécie" in rows[0]
                    or "Estratificação" in rows[0]
                    or "Data de Nascimento" in rows[0]
                ):
                    rows.pop(0)

                i = 0
                while i + 2 < len(rows):
                    nr_brinco = rows[i].strip()
                    nr_manejo = rows[i + 1].strip()
                    info = rows[i + 2].strip().split()

                    if (
                        nr_brinco.isdigit() and len(nr_brinco) >= 10 and
                        nr_manejo.isdigit() and len(nr_manejo) < 10 and
                        len(info) >= 5
                    ):
                        especie = info[0]
                        sexo = info[1]
                        idade_anos = info[2]
                        idade_meses = info[3]
                        dt_nascimento = info[4]

                        all_registers.append({
                            'dtRebanho': date,
                            'idUnidadeExploracao': str(idUnidadeExploracao),
                            'nrBrinco': nr_brinco,
                            'nrManejo': nr_manejo,
                            'especie': especie,
                            'sexo': sexo,
                            'Anos': int(idade_anos) if idade_anos.isdigit() else None,
                            'Meses': int(idade_meses) if idade_meses.isdigit() else None,
                            'dtNasc': dt_nascimento
                        })
                        i += 3
                    else:
                        i += 1

            except Exception as e:
                output['errors']["parsing_error"] = True
                output['errors']["error_message"] = f"Erro ao processar PDF da UEP {idUnidadeExploracao}: {str(e)}"
                return output

        if all_registers:
            try:

                    # Dataframe dos registros
                    dfRebanho = pd.DataFrame(all_registers)

                    # Usa o DuckDB para ler e filtrar, removendo a coluna 'especie'
                    con = duckdb.connect()
                    at_rebanho = con.execute("""
                        SELECT 
                            dtRebanho,
                            idUnidadeExploracao,
                            nrBrinco,
                            nrManejo,
                            sexo,
                            Anos,
                            Meses,
                            dtNasc
                        FROM dfRebanho
                    """).arrow()

                    output["atRebanho"] = at_rebanho
                    #fecha a conexão
                    con.close()

            except Exception as e:
                output['errors']["data_error"] = True
                output['errors']["error_message"] = f"Erro ao processar com DuckDB: {str(e)}"
        else:
            output['errors']["data_error"] = True
            output['errors']["error_message"] = "Nenhum dado encontrado ou PDF sem estrutura válida."

    except Exception as e:
        output['errors']["data_error"] = True
        output['errors']["error_message"] = f"Erro inesperado no processamento: {str(e)}"

    return output


# Uso


# ueps = [267401] # uep do código oficial 253763
# date = '10/02/2025'

# login = sigen_authenticate(user,password)

# if login['login_error'] == False:
#     session = login['session']


# resultado = get_atRebanho(ueps, date,session)

# if resultado['errors']["response_error"] == True:
#     print('response error '+ resultado['errors']['error_message'])
#     if resultado['errors']["parsing_error"] == True:
#         print('parsing error '+ resultado['errors']['error_message'])
#         if resultado['errors']["data_error"] == True:
#             print('data error '+ resultado['errors']['error_message'])
# else:
#     display(resultado["atRebanho"].to_pandas())  


# get_atExame: Função que gera uma Arrow Table de código de exames PNCEBT e data da colheita/inoculação
def get_atExame(cd_oficial, dt_inicio, dt_fim,session):
    output = {
        "atExame": None,
        'errors':{
        "response_error": False,
        "parsing_error": False,
        "data_error": False,
        "error_message": ""
        }
    }

    url = 'https://sigen.cidasc.sc.gov.br/DSA.ControleBruceloseTub/ExamePNCEBT/PerformSearch'

    payload = {
        "id_exame_pncebt": "",
        "cd_oficial": cd_oficial,
        "ds_numero_portaria": "",
        "nm_veterinario": "",
        "dt_inicio": dt_inicio,  # Ex: "01/01/2024"
        "dt_fim": dt_fim,        # Ex: "31/12/2024"
        "cd_entrada_animais": "",
        "cd_unidade_exploracao": "",
        "somente_brucelose": "N",
        "menos_60_dias": "N",
        "eh_receituario_vacinacao_rb51": "N",
        "cs_situacao_Value": "",
        "cs_situacao": "FI",
        "ext-comp-1069_SelIndex": "",
        "cb_produtor_Value": "",
        "cb_produtor": "Documento (CPF/CNPJ) ou Nome e Município",
        "cb_produtor_SelIndex": "",
        "cb_municipio_Value": "",
        "cb_municipio": "Nome ou UF",
        "cb_municipio_SelIndex": ""
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = session.post(url, headers=headers, data=payload)
        response.raise_for_status()
        if "<title>SIGEN+" in response.text and "formLogin" in response.text:
                        output['errors']["response_error"] = True
                        output['errors']["error_message"] = "Usuário não logado"
                        return output
    except Exception as e:
        output['errors']["response_error"] = True
        output['errors']["error_message"] = f"Erro na requisição: {str(e)}"
        return output

    try:
        data_json = response.json()
        if data_json.get("success") and "data" in data_json:
            registros = data_json["data"]

            # Extração e tratamento dos dados
            ids = []
            datas = []
            for rec in registros:
                ids.append(str(rec["id_exame_pncebt"]))
                # Extrai só a parte da data antes do "T", como '2025-05-14'
                datas.append(datetime.fromisoformat(rec["dt_colheita_inoculacao"]).date())

            # Criação da arrow table
            table = pa.table({
                "id_exame_pncebt": pa.array(ids, type=pa.string()),
                "dt_colheita_inoculacao": pa.array(datas)
            })
            con = duckdb.connect()
            con.register('t', table)
            atExame = con.query('SELECT DISTINCT * FROM t').to_arrow_table()
            output["atExame"] = atExame
            con.close()
        else:
            output['errors']['data_error'] = True
            output['errors']["error_message"] = "Resposta inválida ou sem dados"
    except Exception as e:
        output['errors']["parsing_error"] = True
        output['errors']['error_message'] = f"Erro ao processar JSON: {str(e)}"

    return output



# #Uso


# cd_oficial = 253763
# dt_inicio = "10/02/2025"
# dt_fim = "11/04/2025"

# resultado = get_atExame(cd_oficial, dt_inicio, dt_fim)
# if resultado['errors']["response_error"] == True:
#     print('response error '+ resultado['errors']['error_message'])
#     if resultado['errors']["parsing_error"] == True:
#         print('parsing error '+ resultado['errors']['error_message'])
#         if resultado['errors']["data_error"] == True:
#             print('data error '+ resultado['errors']['error_message'])

# else:
#     display(resultado['atExame'].to_pandas())


# get_atExameBrinco: função para gerar uma arrow table com os resultados por animal

def get_atExameBrinco(atExame,session):
    output = {
        "atExameBrinco": None,
       'errors':{
        "response_error": False,
        "parsing_error": False,
        "data_error": False,
        "error_message": ""
        }
    }
    con = duckdb.connect()
    con.execute(""" 
                CREATE TABLE IF NOT EXISTS atExameBrinco (
                    id_exame_pncebt VARCHAR,
                    nrBrinco VARCHAR,
                    ResBru VARCHAR,
                    ResTub VARCHAR,
                    dsTipoObservacao VARCHAR
                );

                """)
    try:
        for id_exame_pncebt in atExame.column('id_exame_pncebt').to_pylist():
            url = f'https://sigen.cidasc.sc.gov.br/DSA.ControleBruceloseTub/ExamePNCEBT/Get/{id_exame_pncebt}'

            try:
                response = session.get(url)
                response.raise_for_status()
                if "<title>SIGEN+" in response.text and "formLogin" in response.text:
                        output['errors']["response_error"] = True
                        output['errors']["error_message"] = "Usuário não logado"
                        return output
            except Exception as e:
                output['erros']["response_error"] = True
                output['errors']["error_message"] = f"Erro na requisição do exame {id_exame_pncebt}: {str(e)}"
                return output

            try:
                json_data = response.json()
                examinados = json_data['data']['listaExameBrinco']['Current']
                ext = pa.Table.from_pylist(examinados)
                ext = ext.append_column('id_exame_pncebt', pa.array([str(id_exame_pncebt)] * len(ext)))

                query = """ 
                        INSERT INTO atExameBrinco
                            SELECT
                                id_exame_pncebt,
                                nrBrincoNovo AS nrBrinco,
                                CASE
                                    WHEN csResultadoFCBrucelose <> '' THEN CONCAT('PF ', dsResultadoFCBrucelose)
                                    WHEN csResultado2MEBrucelose <> '' THEN CONCAT('2ME ', dsResultado2MEBrucelose)
                                    WHEN csResultadoAATBrucelose <> '' THEN dsResultadoAATBrucelose
                                    ELSE ''
                                END AS ResBru,
                                CASE
                                    WHEN csResultadoTCCTuberculose <> '' THEN dsResultadoTCCTuberculose
                                    WHEN csResultadoTCSTuberculose <> '' THEN dsResultadoTCSTuberculose
                                    ELSE ''
                                END AS ResTub,
                                dsTipoObservacao
                            FROM ext

                        """
                con.register('ext',ext)
                con.execute(query)
            except Exception as e:
                output['errors']['parsing_error'] = True
                output['errors']['error_message'] = str(e)
        atExameBrinco = con.execute('SELECT * FROM AtExameBrinco').arrow()
        output['atExameBrinco'] = atExameBrinco
    except Exception as e:
        output['errors']['data_error'] = True
        output['errors']['error_message'] = str(e)
    return output



#Uso


# cd_oficial = 253763
# dt_inicio = "10/02/2025"
# dt_fim = "11/04/2025"

# resultado = get_atExame(cd_oficial, dt_inicio, dt_fim)
# if resultado['errors']["response_error"] == True:
#     print('response error '+ resultado['errors']['error_message'])
#     if resultado['errors']["parsing_error"] == True:
#         print('parsing error '+ resultado['errors']['error_message'])
#         if resultado['errors']["data_error"] == True:
#             print('data error '+ resultado['errors']['error_message'])

# else:
#     atExame = resultado['atExame']
#     resultado2 = get_atExameBrinco(atExame)
#     if resultado2['errors']["response_error"] == True:
#         print('response error '+ resultado2['errors']['error_message'])
#     if resultado2['errors']["parsing_error"] == True:
#         print('parsing error '+ resultado2['errors']['error_message'])
#         if resultado2['errors']["data_error"] == True:
#             print('data error '+ resultado2['errors']['error_message'])
#     else:
#         atExameBrinco = resultado2['atExameBrinco']
#         display(atExameBrinco.to_pandas())       



# get_dfRebanhoExame: função para gerar o dataframe final da análise

def get_dfRebanhoExame(cd_oficial, date,session):
    output = {
        "dfRebanhoExame": pd.DataFrame(),
        "errors": {
            "function_error": False,
            "function_error_message": "",
            "get_ueps": {
                "response_error": False,
                "parsing_error": False,
                "data_error": False,
                "error_message": ""
            },
            "get_atRebanho": {
                "response_error": False,
                "parsing_error": False,
                "data_error": False,
                "error_message": ""
            },
            "get_atExame": {
                "response_error": False,
                "parsing_error": False,
                "data_error": False,
                "error_message": ""
            },
            "get_atExameBrinco": {
                "response_error": False,
                "parsing_error": False,
                "data_error": False,
                "error_message": ""
            }
        }
    }

    # Inicializa as variáveis para evitar erro de variável não definida
    ueps = None
    atRebanho = None
    atExame = None
    atExameBrinco = None

    # 1. get_ueps
    try:
        result_ueps = get_ueps(cd_oficial,session)
        if result_ueps['ueps'] is None:
            output['errors']['get_ueps'] = result_ueps['errors']
        else:
            ueps = result_ueps['ueps']
    except Exception as e:
        output['errors']['function_error'] = True
        output['errors']['function_error_message'] = 'get_ueps error ' + str(e)

    # 2. get_atRebanho (só se ueps existir)
    if ueps is not None:
        try:
            result_rebanho = get_atRebanho(ueps, date,session)
            if result_rebanho['atRebanho'] is None:
                output['errors']['get_atRebanho'] = result_rebanho['errors']
            else:
                atRebanho = result_rebanho['atRebanho']
        except Exception as e:
            output['errors']['function_error'] = True
            output['errors']['function_error_message'] = 'get_atRebanho error ' + str(e)

    # 3. get_atExame (só se atRebanho existir)
    if atRebanho is not None:
        try:
            dt_inicio = date
            dt_fim = (datetime.strptime(dt_inicio, '%d/%m/%Y') + timedelta(days=60)).strftime('%d/%m/%Y')

            result_exame = get_atExame(cd_oficial, dt_inicio, dt_fim,session)

            if result_exame['atExame'] is None:
                output['errors']['get_atExame'] = result_exame['errors']
            else:
                atExame = result_exame['atExame']
        except Exception as e:
            output['errors']['function_error'] = True
            output['errors']['function_error_message'] = 'get_atExame error ' + str(e)

    # 4. get_atExameBrinco (só se atExame existir)
    if atExame is not None:
        try:
            result_ExameBrinco = get_atExameBrinco(atExame,session)
            if result_ExameBrinco['atExameBrinco'] is None:
                output['errors']['get_atExameBrinco'] = result_ExameBrinco['errors']
            else:
                atExameBrinco = result_ExameBrinco['atExameBrinco']
        except Exception as e:
            output['errors']['function_error'] = True
            output['errors']['function_error_message'] = 'get_atExameBrinco error ' + str(e)

    # 5. cruzar dados e gerar dfRebanhoExame (só se atExameBrinco existir)
    if atExameBrinco is not None:
        try:
            con = duckdb.connect()
            con.register('atRebanho', atRebanho)
            con.register('atExame', atExame)
            con.register('atExameBrinco', atExameBrinco)

            with open('cross_rebanho_exame.sql', 'r', encoding='utf-8') as f:
                query = f.read()

            dfRebanhoExame = con.execute(query).fetch_df()
            output['dfRebanhoExame'] = dfRebanhoExame

        except Exception as e:
            output['errors']['function_error'] = True
            output['errors']['function_error_message'] = 'Erro ao cruzar dados de rebanho com exames: ' + str(e)

    return output

# Uso

# cd_oficial = 253763
# date = '10/02/2025'
# login = sigen_authenticate(user,password)

# if login['login_error'] == False:
#     session = login['session']
# else:
#     print('erro de login '+ login['error_message'])

# resultado = get_dfRebanhoExame(cd_oficial, date,session)
# df = resultado['dfRebanhoExame']

# if not df.empty:
#     display(df)  # Exibe o DataFrame se estiver em notebook
# else:
#     print("Nenhum dado retornado. Erros detectados:")

#     if resultado['errors']['function_error']:
#         print("Erro geral:")
#         print(resultado['errors']['function_error_message'])

#     for etapa, info in resultado['errors'].items():
#         if etapa in ['function_error', 'function_error_message']:
#             continue

#         if any([
#             info.get('response_error'),
#             info.get('parsing_error'),
#             info.get('data_error'),
#             info.get('error_message')
#         ]):
#             print(f"\nErro em {etapa}:")
#             if info.get('response_error'):
#                 print(" - response_error: True")
#             if info.get('parsing_error'):
#                 print(" - parsing_error: True")
#             if info.get('data_error'):
#                 print(" - data_error: True")
#             if info.get('error_message'):
#                 print(" - Mensagem:", info.get('error_message'))

