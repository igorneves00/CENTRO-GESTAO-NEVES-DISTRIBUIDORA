# Centro de Gestao - Neves Distribuidora

Sistema em Python + Streamlit para transformar vendas, estoque, produtos e clientes em indicadores, diagnosticos, alertas e recomendacoes.

## Status da entrega

Esta versao entrega a Etapa 1 funcional:

- Estrutura modular do projeto.
- Leitura dos quatro arquivos reais em `dados/`.
- Tratamento de encoding, separador, cabecalho deslocado, datas e numeros com virgula decimal.
- Relacionamentos entre vendas, clientes, estoque e produtos.
- Banco SQLite criado automaticamente em `data/neves_gestao.db`.
- Pagina de Atualizacao de Dados.
- Pagina Visao Geral com indicadores, rankings, diagnostico e exportacao.
- Paginas das etapas seguintes preparadas com analises reais quando os dados permitem.

## Instalacao local

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

## Arquivos de dados

Os arquivos iniciais ficam em:

```text
dados/
```

Arquivos carregados nesta entrega:

- `vendas 01.13.csv`
- `estoque 13.07.26.csv`
- `produtos 13.07.26.csv`
- `Listagem de clientes 13.07.26.csv`

Novos arquivos devem ser enviados pela pagina **Atualizacao de Dados**.

## Diagnostico dos arquivos reais

### Vendas

- Arquivo: `vendas 01.13.csv`
- Encoding detectado: `cp1252`
- Separador detectado: `;`
- Registros lidos: `24.065`
- Registros validos pelos status iniciais `FATURADO` e `PAGO`: `23.954`
- Registros invalidos por status: `111`
- Datas invalidas: `0`
- Valores invalidos em quantidade ou valor: `0`
- Possiveis duplicidades por pedido, produto, quantidade e valor: `48`
- Periodo encontrado: gravado no historico de importacoes ao reprocessar.

Colunas encontradas:

```text
VENDEDOR, CLIENTE, RAZAO_SOCIAL, VENDA, DATA_VENDA, STATUS, COD_PRODUTO,
DESCRICAO_VENDA, UNIDADE, QTDE, VALOR_UNITARIO, VALOR_TOTAL, CUSTO_NF,
CUSTO_MEDIO, CUSTO_CHEIO, CUSTO_BASE, DESCONTO, TOTAL_VENDA, GRUPO, FORNECEDOR
```

### Estoque

- Arquivo: `estoque 13.07.26.csv`
- Encoding detectado: `cp1252`
- Separador detectado: `;`
- Registros lidos: `1.154`
- Produtos zerados: `59`
- Produtos negativos: `0`
- Duplicidades por codigo: `0`
- Valores invalidos em estoque/custo: `0`

Colunas principais criadas:

```text
ESTOQUE_TOTAL = DEPOSITO + BALCAO
VALOR_ESTOQUE = ESTOQUE_TOTAL * CUSTO
```

### Produtos

- Arquivo: `produtos 13.07.26.csv`
- Encoding detectado: `cp1252`
- Separador detectado: `;`
- Cabecalho verdadeiro detectado na linha: `5`
- Registros de produtos lidos: `1.194`
- Duplicidades por codigo: `0`

### Clientes

- Arquivo: `Listagem de clientes 13.07.26.csv`
- Encoding detectado: `cp1252`
- Separador detectado: `;`
- Cabecalho verdadeiro detectado na linha: `5`
- Registros de clientes lidos: `209`
- Datas invalidas ou vazias em ultima compra: `5`
- Duplicidades por codigo: `0`

## Diagnostico de relacionamento

- Clientes encontrados no cadastro: `203`
- Clientes das vendas sem correspondencia no cadastro: `1`
- Produtos vendidos encontrados no estoque: `907`
- Produtos vendidos sem correspondencia no estoque: `24`
- Produtos vendidos encontrados no cadastro de produtos: `931`
- Produtos vendidos sem correspondencia no cadastro de produtos: `0`

Nenhum registro problemático e excluido silenciosamente. O diagnostico fica visivel na Visao Geral e na Atualizacao de Dados.

## Calculos principais

- **Pedido:** coluna `VENDA`.
- **Produto vendido:** soma da coluna `QTDE`.
- **Faturamento por produto:** coluna `VALOR_TOTAL`; quando necessario, usa `QTDE * VALOR_UNITARIO`.
- **Faturamento geral:** usa `TOTAL_VENDA` sem duplicar pedido quando disponivel; caso contrario soma `VALOR_ITEM`.
- **Ticket medio:** faturamento dividido pelo numero de pedidos.
- **Estoque total:** `DEPOSITO + BALCAO`.
- **Valor do estoque:** `ESTOQUE_TOTAL * CUSTO`.
- **Clientes inativos:** clientes com 60 dias ou mais desde a ultima compra.
- **Curva ABC:** recalculada pelo periodo filtrado, com A ate 80%, B ate 95% e C acima de 95% do acumulado.
- **Cobertura de estoque:** estoque atual dividido pelo consumo medio diario.
- **Ponto de reposicao:** consumo medio diario vezes prazo de entrega mais dias de seguranca.

## Dados que ainda faltam

- Estoque minimo e maximo por produto.
- Prazo especifico por fornecedor.
- Historico detalhado de compras.
- Cadastro de fornecedores.
- Cotacoes.
- Metas por vendedor, cidade, grupo, novos clientes e reativacao.
- Responsavel comercial cadastrado diretamente por cliente.

## GitHub

1. Crie um repositorio vazio no GitHub.
2. No terminal, dentro da pasta do projeto:

```bash
git init
git add .
git commit -m "Primeira versao do Centro de Gestao Neves"
git branch -M main
git remote add origin URL_DO_REPOSITORIO
git push -u origin main
```

## Streamlit Community Cloud

1. Publique o projeto no GitHub.
2. Acesse Streamlit Community Cloud.
3. Crie um novo app apontando para o repositorio.
4. Configure:

```text
Main file path: app.py
```

5. Garanta que os arquivos CSV estejam na pasta `dados/`.
6. Se futuramente usar API de IA, cadastre a chave em secrets, nunca no codigo.

## Observacoes tecnicas

- O banco local fica em `data/neves_gestao.db`.
- A meta mensal inicial e R$ 500.000 e pode ser alterada em Configuracoes.
- A primeira versao da Neves IA usa regras e Pandas, sem API paga.
- Erros de execucao sao registrados em `logs/app.log`.
