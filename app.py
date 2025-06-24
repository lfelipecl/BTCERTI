import base64
import io
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
from sigen_api import sigen_authenticate, get_dfRebanhoExame

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

sessao_atual = {}

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("BTCerti - Análise de Processos de Certificação PNCEBT CIDASC"), className="text-center mt-4 mb-4")),
    
    dbc.Row([
        dbc.Col([
            dbc.Label("Usuário"),
            dbc.Input(id="input-usuario", placeholder="Digite seu usuário do Sigen+", type="text"),
        ], width=4),

        dbc.Col([
            dbc.Label("Senha"),
            dbc.Input(id="input-senha", placeholder="Digite sua senha", type="password"),
        ], width=4),

        dbc.Col([
            dbc.Button("Entrar", id="btn-entrar", color="primary", className="mt-4"),
        ], width=4)
    ]),

    html.Hr(),

    dbc.Row([
        dbc.Col([
            dbc.Label("Código Oficial"),
            dbc.Input(id="input-codigo", type="number", disabled=True),
        ], width=4),

        dbc.Col([
            dbc.Label("Data (DD/MM/AAAA)"),
            dbc.Input(id="input-data", placeholder="DD/MM/AAAA", disabled=True),
        ], width=4),

        dbc.Col([
            dbc.Button("Gerar Relatório", id="btn-relatorio", color="success", disabled=True),
            dbc.Button("Sair", id="btn-sair", color="danger", disabled=True, className="ms-2"),
        ], width=4),
    ], className="mb-3"),

    dbc.Row([
        dbc.Col(dcc.Loading(
            id="loading-relatorio",
            type="default",
            children=html.Div(id="msg-relatorio", style={"color": "red", "fontWeight": "bold"})
        )),
    ]),

    dbc.Row([
        dbc.Col(dcc.Loading(
            id="loading-tabela",
            type="default",
            children=html.Div(id="div-tabela")
        )),
    ]),

    dbc.Row([
        dbc.Col(dcc.Loading(
            id="loading-download",
            type="default",
            children=html.Div(id="link-download", className="mt-2")
        )),
    ]),
], fluid=True)


def normalizar_data(data_str):
    data_str = data_str.strip()
    if '/' in data_str:
        try:
            dt = datetime.strptime(data_str, '%d/%m/%Y')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            return None
    else:
        if len(data_str) == 8 and data_str.isdigit():
            try:
                dt = datetime.strptime(data_str, '%d%m%Y')
                return dt.strftime('%d/%m/%Y')
            except ValueError:
                return None
        else:
            return None


@app.callback(
    Output("input-usuario", "disabled"),
    Output("input-senha", "disabled"),
    Output("input-codigo", "disabled"),
    Output("input-data", "disabled"),
    Output("btn-entrar", "disabled"),
    Output("btn-relatorio", "disabled"),
    Output("btn-sair", "disabled"),
    Output("msg-relatorio", "children"),
    Output("div-tabela", "children"),
    Output("link-download", "children"),
    Input("btn-entrar", "n_clicks"),
    Input("btn-relatorio", "n_clicks"),
    Input("btn-sair", "n_clicks"),
    State("input-usuario", "value"),
    State("input-senha", "value"),
    State("input-codigo", "value"),
    State("input-data", "value"),
    prevent_initial_call=True
)
def controle_geral(btn_entrar, btn_relatorio, btn_sair, usuario, senha, codigo, data_texto):
    ctx = callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    botao = ctx.triggered[0]['prop_id'].split('.')[0]

    global sessao_atual

    # Logout
    if botao == "btn-sair":
        sessao_atual.clear()
        return False, False, True, True, False, True, True, "", "", ""

    # Login
    elif botao == "btn-entrar":
        if not usuario or not senha:
            return False, False, True, True, False, True, True, "Informe usuário e senha.", "", ""

        auth = sigen_authenticate(usuario, senha)
        if auth.get('login_error'):
            msg = f"Erro de login: {auth.get('error_message', 'Desconhecido')}"
            return False, False, True, True, False, True, True, msg, "", ""

        sessao_atual['session'] = auth['session']
        # Desabilita login e habilita inputs e botões principais
        return True, True, False, False, True, False, False, "Login realizado com sucesso.", "", ""

    # Gerar relatório
    elif botao == "btn-relatorio":
        if 'session' not in sessao_atual:
            return True, True, True, True, True, True, False, "Faça login primeiro.", "", ""

        if not codigo:
            return True, True, False, False, True, False, False, "Código Oficial não informado.", "", ""

        if not data_texto:
            return True, True, False, False, True, False, False, "Data não informada.", "", ""

        data_formatada = normalizar_data(data_texto)
        if not data_formatada:
            return True, True, False, False, True, False, False, "Formato de data inválido. Use DD/MM/AAAA ou DDMMAAAA.", "", ""

        resultado = get_dfRebanhoExame(codigo, data_formatada, sessao_atual['session'])
        df = resultado.get("dfRebanhoExame")

        if df is None or df.empty:
            return True, True, False, False, True, False, False, "Nenhum dado retornado.", "", ""

        df_fill = df.fillna("--")
        columns=[{"name": i, "id": i} for i in df_fill.columns]
        data=df_fill.to_dict("records")

        tabela = dash_table.DataTable(
            columns=columns,
            data=data,
            page_size=20,
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "minWidth": "100px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "lightgrey", "fontWeight": "bold"}
        )

        # Gerar arquivo Excel em base64 para link download
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        dt_obj = datetime.strptime(data_formatada, "%d/%m/%Y")
        dt_str = dt_obj.strftime("%d%m%Y")
        nome_arquivo = f"rel_{codigo}-{dt_str}.xlsx"
        href = html.A(
            "📥 Baixar Excel",
            href=f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}",
            download=nome_arquivo,
            target="_blank",
            style={"fontWeight": "bold", "fontSize": "16px"}
        )

        return True, True, False, False, True, False, False, "Relatório gerado com sucesso.", tabela, href

    else:
        raise dash.exceptions.PreventUpdate


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
