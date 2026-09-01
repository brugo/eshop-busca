"""Baixa para assets/ a capa oficial de cada jogo do data.json.

A arte da Nintendo e 16:9 (o CDN entrega 800x450 no maior tamanho util).
Nada de c_fill aqui: qualquer corte come os logos. Roda sem argumentos:

    python fetch-covers.py [--force]

Sem --force, pula os arquivos que ja existem.
"""
import json
import os
import sys
import urllib.request

BASE = 'https://assets.nintendo.com/image/upload/w_640/q_auto:best/f_jpg/store/software/'
FORCE = '--force' in sys.argv

def main():
    with open('data.json', encoding='utf-8') as f:
        games = json.load(f)['games']
    os.makedirs('assets', exist_ok=True)
    baixadas = pulos = falhas = 0
    for g in games:
        if not g.get('img'):
            continue
        destino = os.path.join('assets', g['id'] + '.jpg')
        if os.path.exists(destino) and not FORCE:
            pulos += 1
            continue
        try:
            dados = urllib.request.urlopen(BASE + g['img'], timeout=40).read()
            if len(dados) < 3000:
                raise ValueError('resposta pequena demais (%d bytes)' % len(dados))
            with open(destino, 'wb') as f:
                f.write(dados)
            baixadas += 1
        except Exception as erro:
            falhas += 1
            print('falhou: %s -- %s' % (g['n'], erro))
    print('baixadas=%d puladas=%d falhas=%d' % (baixadas, pulos, falhas))

if __name__ == '__main__':
    main()
