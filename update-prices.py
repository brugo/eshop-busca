# -*- coding: utf-8 -*-
"""Atualiza os precos da eShop BR no data.json e no bloco JSON do index.html.

Fonte: API oficial da Nintendo, sem chave. Ela recusa lotes grandes, entao as
consultas vao de 5 em 5 NSUIDs.

    python update-prices.py

Sai com codigo 0 sempre que a consulta funcionou, tendo mudado preco ou nao.
Imprime na ultima linha "MUDOU=1" ou "MUDOU=0", que a GitHub Action le para
decidir se faz commit.
"""
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

API = 'https://api.ec.nintendo.com/v1/price?country=BR&lang=pt&ids='
LOTE = 5
BRASILIA = timezone(timedelta(hours=-3))
ORDEM = ['n', 'id', 'p', 's', 'reg', 'cur', 'pct', 'ends', 'low', 'phys', 'physSrc',
         'note', 'hist', 'img']


def consulta(ids):
    """Devolve {nsuid: registro} para um lote de ids."""
    url = API + ','.join(ids)
    with urllib.request.urlopen(url, timeout=40) as r:
        dados = json.load(r)
    # A API devolve title_id como numero; o JSON guarda NSUID como string.
    return {str(p['title_id']): p for p in dados.get('prices', [])}


def aplica(jogo, preco, hoje):
    """Escreve os campos de preco no jogo. Devolve True se algo mudou."""
    antes = json.dumps(jogo, sort_keys=True, ensure_ascii=False)

    if preco.get('sales_status') == 'unreleased' or not preco.get('regular_price'):
        return False  # sem preco na loja ainda; nao mexe

    jogo['reg'] = float(preco['regular_price']['raw_value'])
    desconto = preco.get('discount_price')
    if desconto:
        jogo['cur'] = float(desconto['raw_value'])
        jogo['pct'] = int(round((1 - jogo['cur'] / jogo['reg']) * 100))
        jogo['ends'] = desconto.get('end_datetime')
    else:
        jogo.pop('cur', None)
        jogo.pop('pct', None)
        jogo.pop('ends', None)

    atual = jogo.get('cur', jogo['reg'])
    if jogo.get('low') is None or atual < jogo['low']:
        jogo['low'] = atual

    hist = jogo.setdefault('hist', [])
    if hist and hist[-1][0] == hoje:
        hist[-1][1] = atual
    else:
        hist.append([hoje, atual])

    return json.dumps(jogo, sort_keys=True, ensure_ascii=False) != antes


def serializa(dados, ordem=None, cabecalhos=('updated', 'physChecked'), lista='games'):
    """Mesmo formato do arquivo original: um item por linha, chaves na ordem.

    Os outros scripts (fetch-deals.py, read-channel.py) chamam esta funcao para
    os blocos deles, para os tres JSON do projeto nao divergirem de formato.
    """
    ordem = ordem or ORDEM
    linhas = []
    for item in dados[lista]:
        campos = [(k, item[k]) for k in ordem if k in item]
        corpo = ', '.join('%s: %s' % (json.dumps(k), json.dumps(v, ensure_ascii=False))
                          for k, v in campos)
        linhas.append('    {' + corpo + '}')
    topo = ''.join('  %s: %s,\n' % (json.dumps(c), json.dumps(dados[c], ensure_ascii=False))
                   for c in cabecalhos if c in dados)
    return '{\n%s  %s: [\n%s\n  ]\n}\n' % (topo, json.dumps(lista), ',\n'.join(linhas))


def escreve_html(bloco, ident='tracker-data'):
    abre = '<script type="application/json" id="%s">' % ident
    with io.open('index.html', encoding='utf-8') as f:
        html = f.read()
    i = html.index(abre) + len(abre)
    j = html.index('</script>', i)
    html = html[:i] + '\n' + bloco + html[j:]
    with io.open('index.html', 'w', encoding='utf-8', newline='') as f:
        f.write(html)


def main():
    with io.open('data.json', encoding='utf-8') as f:
        dados = json.load(f)
    jogos = dados['games']
    agora = datetime.now(BRASILIA)
    hoje = agora.strftime('%Y-%m-%d')

    ids = [g['id'] for g in jogos if g.get('id')]
    precos = {}
    for i in range(0, len(ids), LOTE):
        lote = ids[i:i + LOTE]
        try:
            precos.update(consulta(lote))
        except Exception as erro:
            print('erro no lote %s: %s' % (lote, erro), file=sys.stderr)
            sys.exit(1)
        time.sleep(0.5)

    faltando = [i for i in ids if i not in precos]
    if faltando:
        print('sem resposta para: %s' % ', '.join(faltando), file=sys.stderr)

    mudou = False
    for jogo in jogos:
        preco = precos.get(jogo.get('id'))
        if preco and aplica(jogo, preco, hoje):
            mudou = True

    dados['updated'] = agora.strftime('%Y-%m-%dT%H:%M:%S-03:00')
    bloco = serializa(dados)
    with io.open('data.json', 'w', encoding='utf-8', newline='') as f:
        f.write(bloco)
    escreve_html(bloco)

    promos = [g for g in jogos if g.get('pct')]
    print('%d jogos consultados, %d em promocao' % (len(precos), len(promos)))
    for g in sorted(promos, key=lambda g: -g['pct']):
        print('  -%d%%  %s  R$ %.2f (de R$ %.2f)' % (g['pct'], g['n'], g['cur'], g['reg']))
    print('MUDOU=%d' % (1 if mudou else 0))


if __name__ == '__main__':
    main()
