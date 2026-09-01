# -*- coding: utf-8 -*-
"""Manda o alerta do Radar da eShop por um bot do Telegram.

Precisa de duas variaveis de ambiente:

    TELEGRAM_TOKEN    token do bot, criado no @BotFather
    TELEGRAM_CHAT_ID  para onde mandar (seu chat com o bot, ou o grupo)

Sem elas o script avisa e sai em silencio, com codigo 0 -- assim a Action nao
quebra enquanto os secrets ainda nao existem.

Modos:

    --resumo                   manda o panorama do dia (mesmo sem promocao)
    --novidades ANTERIOR.json  compara com o estado anterior e so manda se
                               apareceu promocao nova ou o preco caiu
    --simular                  imprime a mensagem em vez de enviar
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request

SITE = 'https://brugo.github.io/eshop-busca/'
LOJA = 'https://www.nintendo.com/pt-br/store/products/%s/'


def brl(valor):
    return ('R$ %.2f' % valor).replace('.', ',')


def carrega(caminho):
    with io.open(caminho, encoding='utf-8') as f:
        return json.load(f)


def por_id(dados):
    return {g['id']: g for g in dados['games']}


def linha_promo(g):
    texto = '<a href="%s">%s</a> -- <b>%s</b>' % (LOJA % g['s'], g['n'], brl(g['cur']))
    texto += ' (era %s, -%d%%)' % (brl(g['reg']), g['pct'])
    if g.get('phys') is not None and g['phys'] < g['cur']:
        texto += '\n   fisico sai mais barato: %s' % brl(g['phys'])
    return texto


def mensagem_resumo(dados):
    promos = sorted([g for g in dados['games'] if g.get('pct')],
                    key=lambda g: -g['pct'])
    if promos:
        cabeca = '<b>Radar da eShop</b> -- %d em promocao hoje' % len(promos)
        corpo = '\n\n'.join(linha_promo(g) for g in promos)
    else:
        cabeca = '<b>Radar da eShop</b>'
        corpo = 'Nenhum jogo da sua lista esta em promocao hoje.'
    return '%s\n\n%s\n\n<a href="%s">Ver a lista completa</a>' % (cabeca, corpo, SITE)


def linha_fisico(g):
    origem = g.get('physSrc') or {}
    texto = '<a href="%s">%s</a> -- <b>%s</b> em midia fisica' % (
        origem.get('url', SITE), g['n'], brl(g['phys']))
    if origem.get('loja'):
        texto += ' (%s)' % origem['loja']
    digital = g.get('cur') or g.get('reg')
    if digital is not None and g['phys'] < digital:
        texto += '\n   %s a menos que o digital' % brl(digital - g['phys'])
    return texto


def mensagem_novidades(dados, anterior):
    velhos = por_id(anterior)
    novidades = []
    for g in dados['games']:
        se_antes = velhos.get(g['id'])
        if not se_antes:
            continue
        entrou = g.get('pct') and not se_antes.get('pct')
        baixou = (g.get('cur') is not None and se_antes.get('cur') is not None
                  and g['cur'] < se_antes['cur'])
        if entrou or baixou:
            novidades.append((g, 'nova' if entrou else 'baixou mais'))

    fisicos = []
    for g in dados['games']:
        se_antes = velhos.get(g['id'])
        if not se_antes or g.get('phys') is None:
            continue
        # So avisa quando o canal trouxe preco fisico novo e menor que o anterior.
        if se_antes.get('phys') is None or g['phys'] < se_antes['phys']:
            if g.get('physSrc'):
                fisicos.append(g)

    if not novidades and not fisicos:
        return None
    linhas = []
    for g, motivo in sorted(novidades, key=lambda p: -p[0]['pct']):
        marca = 'PROMOCAO NOVA' if motivo == 'nova' else 'PRECO CAIU'
        linhas.append('%s\n%s' % (marca, linha_promo(g)))
    for g in fisicos:
        linhas.append('MIDIA FISICA\n%s' % linha_fisico(g))
    return '<b>Radar da eShop</b>\n\n%s\n\n<a href="%s">Ver a lista completa</a>' % (
        '\n\n'.join(linhas), SITE)


def envia(texto, token, chat):
    url = 'https://api.telegram.org/bot%s/sendMessage' % token
    corpo = urllib.parse.urlencode({
        'chat_id': chat,
        'text': texto,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'true',
    }).encode('utf-8')
    with urllib.request.urlopen(url, data=corpo, timeout=30) as r:
        resposta = json.load(r)
    if not resposta.get('ok'):
        raise RuntimeError('Telegram recusou: %s' % resposta)


def imprime(texto):
    """Imprime sem quebrar em console que nao aceita acento."""
    saida = sys.stdout
    codificacao = getattr(saida, 'encoding', None) or 'ascii'
    saida.write(texto.encode(codificacao, 'replace').decode(codificacao) + '\n')


def main():
    args = sys.argv[1:]
    simular = '--simular' in args
    dados = carrega('data.json')

    if '--novidades' in args:
        caminho = args[args.index('--novidades') + 1]
        texto = mensagem_novidades(dados, carrega(caminho))
        if texto is None:
            print('sem novidade para avisar')
            return
    else:
        texto = mensagem_resumo(dados)

    if simular:
        imprime(texto)
        return

    token = os.environ.get('TELEGRAM_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        print('TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID ausente; nada foi enviado')
        return

    envia(texto, token, chat)
    print('alerta enviado')


if __name__ == '__main__':
    main()
