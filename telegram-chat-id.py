# -*- coding: utf-8 -*-
"""Descobre o chat_id para onde o bot deve mandar os alertas.

Uso, na sua maquina (o token vem da variavel de ambiente, nunca por argumento,
para nao ficar gravado no historico do terminal):

    PowerShell:  $env:TELEGRAM_TOKEN = "cole aqui"; python telegram-chat-id.py
    Git Bash:    TELEGRAM_TOKEN="cole aqui" python telegram-chat-id.py

Antes de rodar, mande qualquer mensagem para o bot no chat privado (e, se for
usar o grupo, mande uma mensagem no grupo com o bot ja adicionado). O Telegram
so mostra conversas que tiveram atividade recente.

O script nao imprime o token e nao consome as mensagens da fila.
"""
import json
import os
import sys
import urllib.request


def chama(token, metodo):
    url = 'https://api.telegram.org/bot%s/%s' % (token, metodo)
    with urllib.request.urlopen(url, timeout=30) as r:
        resposta = json.load(r)
    if not resposta.get('ok'):
        raise RuntimeError('Telegram recusou %s: %s' % (metodo, resposta))
    return resposta['result']


def main():
    token = os.environ.get('TELEGRAM_TOKEN')
    if not token:
        print('Defina TELEGRAM_TOKEN antes de rodar. Veja o cabecalho do arquivo.')
        sys.exit(1)

    eu = chama(token, 'getMe')
    print('bot: @%s (%s)' % (eu.get('username'), eu.get('first_name')))

    vistos = {}
    for u in chama(token, 'getUpdates'):
        msg = u.get('message') or u.get('channel_post') or {}
        chat = msg.get('chat')
        if chat:
            vistos[chat['id']] = chat

    if not vistos:
        print('')
        print('Nenhuma conversa recente. Mande uma mensagem para o bot (ou no')
        print('grupo, com ele ja dentro) e rode de novo.')
        return

    print('')
    print('Conversas encontradas:')
    for cid, chat in vistos.items():
        nome = chat.get('title') or chat.get('username') or chat.get('first_name') or '?'
        print('  chat_id %-16s  %-8s  %s' % (cid, chat.get('type'), nome))
    print('')
    print('Use o chat_id do tipo "private" para receber os alertas voce mesmo.')
    print('Guarde com:  gh secret set TELEGRAM_CHAT_ID --repo brugo/eshop-busca')


if __name__ == '__main__':
    main()
