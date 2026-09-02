# -*- coding: utf-8 -*-
"""Coleta as promocoes da eShop BR inteira, nao so as da lista de desejos.

Fonte: o mesmo indice de busca que a loja da Nintendo usa no navegador
(Algolia, indice store_game_pt_br). A chave abaixo e a publica, de leitura, que
a loja entrega para qualquer visitante -- nao e credencial de ninguem.

A eShop BR costuma ter ~3500 jogos em promocao, quase todos irrelevantes. O
corte e por popularidade (`popularityRank` do proprio indice), que separa jogo
conhecido de shovelware sem precisar julgar qualidade.

    python fetch-deals.py [--simular]
"""
import io
import json
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

APP = 'U3B6GR4UA3'
CHAVE = 'a29c6927638bfd8cee23993e51e721c9'
INDICE = 'store_game_pt_br'
QUANTOS = 60          # quantos entram na aba
BRASILIA = timezone(timedelta(hours=-3))
ORDEM = ['n', 'id', 'p', 's', 'reg', 'cur', 'pct', 'ends', 'rank', 'meu', 'img']


def consulta():
    url = 'https://%s-dsn.algolia.net/1/indexes/%s/query' % (APP.lower(), INDICE)
    filtro = urllib.parse.quote('topLevelFilters:"Promoções"')
    corpo = json.dumps({'params': 'query=&hitsPerPage=1000&filters=' + filtro})
    req = urllib.request.Request(
        url, data=corpo.encode('utf-8'),
        headers={'X-Algolia-API-Key': CHAVE,
                 'X-Algolia-Application-Id': APP,
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def chave_titulo(titulo):
    t = unicodedata.normalize('NFKD', titulo)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())


def main():
    simular = '--simular' in sys.argv

    with io.open('data.json', encoding='utf-8') as f:
        meus = {g['id'] for g in json.load(f)['games']}

    resposta = consulta()
    achados = []
    for h in resposta.get('hits', []):
        preco = h.get('price') or {}
        if not preco.get('percentOff') or not preco.get('finalPrice'):
            continue
        imagem = h.get('productImage') or ''
        prefixo = 'store/software/'
        if imagem.startswith(prefixo):
            imagem = imagem[len(prefixo):]
        achados.append({
            'n': h.get('title', '').strip(),
            'id': str(h.get('nsuid') or h.get('objectID')),
            'p': 'SW2' if h.get('platform') == 'Nintendo Switch 2' else 'SW',
            's': h.get('urlKey', ''),
            'reg': round(float(preco['regPrice']), 2) if preco.get('regPrice') else None,
            'cur': round(float(preco['finalPrice']), 2),
            'pct': int(round(float(preco['percentOff']))),
            'ends': (h.get('eshopDetails') or {}).get('discountPriceEnd'),
            'rank': h.get('popularityRank') or 999999,
            'meu': str(h.get('nsuid')) in meus,
            'img': imagem,
        })

    # O mesmo jogo aparece nas duas geracoes; fica o mais barato.
    melhores = {}
    for jogo in achados:
        k = chave_titulo(jogo['n'])
        if k not in melhores or jogo['cur'] < melhores[k]['cur']:
            melhores[k] = jogo

    # A ordem final e a de popularidade, nao a de desconto: ordenar por desconto
    # joga shovelware de -80% para cima e enterra o jogo bom com -35%.
    lista = sorted(melhores.values(), key=lambda j: j['rank'])[:QUANTOS]

    agora = datetime.now(BRASILIA)
    dados = {
        'updated': agora.strftime('%Y-%m-%dT%H:%M:%S-03:00'),
        'total': resposta.get('nbHits'),
        'games': lista,
    }

    enc = sys.stdout.encoding or 'ascii'

    def fala(t):
        sys.stdout.write(t.encode(enc, 'replace').decode(enc) + '\n')

    fala('%d jogos em promocao na eShop BR; %d escolhidos por popularidade'
         % (resposta.get('nbHits', 0), len(lista)))
    for jogo in lista[:8]:
        fala('  -%d%%  %s  R$ %.2f' % (jogo['pct'], jogo['n'][:44], jogo['cur']))

    if simular:
        fala('modo simulacao: nada foi gravado')
        return

    precos = __import__('importlib.util', fromlist=['util'])
    spec = precos.spec_from_file_location('update_prices', 'update-prices.py')
    modulo = precos.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    bloco = modulo.serializa(dados, ORDEM, ('updated', 'total'), 'games')
    with io.open('deals.json', 'w', encoding='utf-8', newline='') as f:
        f.write(bloco)
    modulo.escreve_html(bloco, 'deals-data')
    fala('deals.json e index.html atualizados')


if __name__ == '__main__':
    main()
