# -*- coding: utf-8 -*-
"""chatbot.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1mhQ8B9TuKXGWRShAUFVUe6uvWxhXnZhj
"""

import numpy as np

from google.colab import drive
drive.mount('/content/drive')

"""# Preparação de Dados"""

from google.colab import auth
auth.authenticate_user()

import gspread
from google.auth import default
creds, _ = default()

gc = gspread.authorize(creds)

worksheet = gc.open('dataset').sheet1
imagem_cardapio = '/content/drive/MyDrive/Chatbot I.A/cardapio.png'

rows = worksheet.get_all_values()
print(rows)

import pandas as pd
df=pd.DataFrame(rows[1:],columns=rows[0])

intencoes = ['pedir_cardapio', 'fazer_pedido', 'pedir_conta', 'escolher_entrega', 'definir_pagamento', 'feedback']
xtrain_global = []
ytrain_global = []
for intencao in intencoes:
    lintencao = df[df['conjunto']=='Conjunto de Treino'][intencao].values.tolist()
    xtrain_global += lintencao
    ytrain_global += [intencao]*len(lintencao)

xtest = []
ytest = []
for intencao in intencoes:
    lintencao = df[df['conjunto']=='Conjunto de Teste'][intencao].values.tolist()
    xtest += lintencao
    ytest += [intencao]*len(lintencao)

"""### split de treino em validação e treino"""

import sklearn.model_selection as model_selection

xtrain,xval,ytrain,yval = model_selection.train_test_split(xtrain_global,ytrain_global,test_size=0.20,stratify=ytrain_global)

np.unique(ytrain,return_counts=True)

"""## pré-processamento

O pré-processamento consiste em transformar todas as sentenças em vetores utilizando sentence-embeddings 
"""

!pip install -U sentence-transformers

from sentence_transformers import SentenceTransformer

converter = SentenceTransformer('multi-qa-distilbert-cos-v1')

xtrain_emb = converter.encode(xtrain)
xval_emb = converter.encode(xval)
xtest_emb = converter.encode(xtest)

"""# Indução do Modelo"""

import sklearn.neighbors as neighbors

model = neighbors.KNeighborsClassifier(n_neighbors=5)

model.fit(xtrain_emb,ytrain)

"""# Ajuste de parâmetros"""

import sklearn.metrics as metrics

for i in range(1,15,2):
    model = neighbors.KNeighborsClassifier(n_neighbors=i,weights="distance")
    model.fit(xtrain_emb,ytrain)
    pred = model.predict(xval_emb)
    print(f"k={i}")
    print(metrics.classification_report(yval,pred))

"""# Avaliação do Modelo"""

import sklearn.metrics as metrics

model = neighbors.KNeighborsClassifier(n_neighbors=5,weights="distance")
model.fit(xtrain_emb,ytrain)
pred = model.predict(xtest_emb)
print(f"k={i}")
print(metrics.classification_report(ytest,pred))

"""#Modelo final"""

model.fit(converter.encode(xtrain_global+xtest),ytrain_global+ytest)

from joblib import dump, load

dump(model, 'chatbot.joblib')

modelo_final = load('chatbot.joblib')

"""Definindo funções de processamento

# Construção de um chatbot
"""

def convert_num(n):
    valores = {'um':1,
               'uma':1,
               'dois':2,
               'duas':2,
               'tres':3,
               'quatro':4,
               'cinco':5,
               'seis':6,
               'sete':7,
               'oito':8,
               'nove':9,
               'dez':10}
    ret = 0
    if n.isnumeric():
        ret = int(n)
    else:
        if n in valores.keys():
            ret = valores[n]

    return ret

!pip install unidecode

from nltk.tokenize import TweetTokenizer
from unidecode import unidecode
tknzr = TweetTokenizer()

lista_entidades = [
'item:coca,refrigerante,agua,cerveja,suco',
'item:bacon,calabresa,portuguesa,marguerita,frango com catupiry,muçarela,napolitana,brigadeiro,romeu e julieta,california,quatro queijos,baiana,presunto',
'num:1,2,3,4,5,6,7,8,9,10',
'num:um,dois,tres,quatro,cinco,seis,sete,oito,nove,dez,uma,duas'
]
entidades = dict()
def load_entidades(lista_entidades):
            for line in lista_entidades:
                entidade,valores = line.split(':')
                str_valores = valores[:]
                valores = str_valores.split(',')
                for valor in valores:
                    if valor not in entidades.keys():
                        entidades[valor] = entidade
load_entidades(lista_entidades)

lista_sinonimos = {
    'coca:cocas,coca-cola,coca-colas,coquinha,coquinhas',
    'refrigerante:guarana,guaranas,refri,refris,refrigerantes,pepsi,icecola,icecolas,refriko,refrikos,fanta,fantas',
    'suco:limonada,natural,del valle,prats,ades',
    'agua:aguas,aguinha,aguinhas',
    'cerveja:cervejas,bohemia,skol,itaipava,kaiser,heineken,budweiser,brahma,caracu,antarctica,schin,corona,bavaria',    
    'calabresa:calabresas',
    'portuguesa:portuguesas',
    'marguerita:margueritas',
    'california:californias',
    'mucarela:mucarela,muçarelas,mussarela,mussarelas',
    'baiana:baianas',
    'frango com catupiry:frango',
    'bacon:beicom',
    'presunto:presuntos',
    'quatro queijos:tres queijos,cinco queijos',
    'napolitana:napolitanas',
    'brigadeiro:chocolate',
    'romeu e julieta:goiabada,goiaba'
}
sinonimos = dict()
def load_sinonimos(lista_sinonimos):
            for line in lista_sinonimos:
                sinonimo,valores = line.split(':')
                str_valores = valores[:]
                valores = str_valores.split(',')
                for valor in valores:  
                    if valor not in sinonimos.keys():
                        sinonimos[valor] = sinonimo
load_sinonimos(lista_sinonimos)

def find_entidades(texto):
    ret = dict()
    ent = ''
    for token in tknzr.tokenize(texto):
        token = token.lower()
        token = unidecode(token)
        
        # Busca token nas entidades
        if token in entidades.keys():
            ent = entidades[token]

            if ent not in ret.keys():
                ret[ent] = [token]
            elif ent:
                ret[ent] += [token]

        # Busca token nos sinonimos das entidades
        elif token in sinonimos.keys():
            
            for key, value in sinonimos.items():
                  if(token == key):
                      
                      ent = entidades[value]
                      if ent not in ret.items():
                          ret[ent] = [sinonimos[key]]
                      elif ent:
                          ret[ent] += [sinonimos[key]]
                      break
    return ret

def convert_num(n):
    valores = {'um':1,
               'uma':1,
               'dois':2,
               'duas':2,
               'tres':3,
               'quatro':4,
               'cinco':5,
               'seis':6,
               'sete':7,
               'oito':8,
               'nove':9,
               'dez':10}
    ret = 0
    if n.isnumeric():
        ret = int(n)
    else:
        if n in valores.keys():
            ret = valores[n]

    return ret

print(find_entidades('me ve duas fantas'))

valor_cardapio = {
    'calabresa':24.0,
    'marguerita':24.0,
    'muçarela':24.0,
    'portuguesa':24.0,
    'bacon': 27.0,
    'baiana':27.0,
    'frango com catupiry':27.0,
    'presunto':27.0,
    'quatro queijos':27.0,
    'brigadeiro':30.0,
    'california':30.0,
    'napolitana':30.0,
    'romeu e julieta': 30.0,
    'coca':8.0,
    'refrigerante':6.0,
    'agua':3.0,
    'suco':5.0,
    'cerveja': 4.0
}

def str_menu(h):
    rstr = ''
    for item in h:
        rstr += f"{item:<10}  {h[item]:>5}\n"
    return rstr

"""# Criação bot para integração com Telegram

---

Intalando biblioteca e importando módulos para o telebot
"""

!pip install pytelegrambotapi --upgrade

"""Definição de chave e criação do telebot"""

import telebot
chave = ("5267043465:AAFEcnGNMHFpx8eZ9fA7jShtdZqA_LM6KbI")
bot = telebot.TeleBot(chave)

"""Definição função para enviar imagens"""

import requests
def enviar_imagem(file_path, chat_id):
    body = {
        'chat_id': chat_id,
    }
    files = {
        'photo': open(file_path, 'rb')
    }
    r = requests.post('https://api.telegram.org/bot{}/sendPhoto'.format(chave), data=body, files=files)

"""# Execução Completa (Menu interativo)"""

# Definição de variáveis para pedidos e conta
pedidos = []
conta = {}

# Definição de função para inicializar bot
@bot.message_handler(commands=["start"])
def inicia(mensagem_usuario):
    bot.send_message(mensagem_usuario.chat.id, "Seja bem vindo a J&G Pizzaria. Vou enviar nosso cardápio para você fazer seu pedido.\n")
    bot.send_message(mensagem_usuario.chat.id, "Você pode pedir para vê-lo novamente a qualquer momento enviando uma mensagem no chat.\n")
    enviar_imagem(imagem_cardapio, mensagem_usuario.chat.id)

# Definição de função resposta ao receber mensagem no Telegram
@bot.message_handler()
def responder(mensagem_usuario):

    # Define mensagem recebida e resposta a ser enviada
    mensagem = mensagem_usuario.text
    resposta = ''

    # Processa a intenção da mensagem recebida
    pred = modelo_final.predict([converter.encode(mensagem)])[0]

    # Predição para mostrar o cardápio
    if pred == 'pedir_cardapio':
        resposta = 'Cardápio encaminhado para você fazer seu pedido.'
        enviar_imagem(imagem_cardapio, mensagem_usuario.chat.id)

    # Intenção para fazer o pedido
    elif pred == 'fazer_pedido':
        # Busca entidades na mensagem
        ent = find_entidades(mensagem)

        # Armazena os itens do pedido em uma lista
        joined = [[x,y] for x,y in zip(ent['num'],ent['item'])]
        pedidos.append(joined)
        
        # Processa pedidos e respostas correspondente
        resposta += 'Pedido anotado: \n'
        for n,item in joined[:-1]:
            if(convert_num(n) > 1): # Verifica plural na resposta do pedido
                resposta += '- %s %ss \n'%(n,item)
            else:
                resposta += '- %s %s \n'%(n,item)
        if(convert_num(joined[-1][0]) > 1): # Verifica plural na resposta do pedido
            resposta += ('- %s %ss\n'%(joined[-1][0],joined[-1][1]))
        else: 
            resposta += ('- %s %s\n'%(joined[-1][0],joined[-1][1]))
        resposta += 'Você pode fazer novos pedidos ou pedir a conta.'
    
    # Intenção para pedir a conta
    elif pred == 'pedir_conta':        
        # Definição das variáveis utilizadas
        total_item = 0
        total_conta = 0
        
        # Processa pedidos e itens para calcular total da conta
        for joined in pedidos:
            for n,item in joined:
                qtd_item = convert_num(n)
                if item in valor_cardapio.keys():
                    preco_item = valor_cardapio[item]
                    total_item += preco_item * qtd_item
            
            # Se item já existe na conta, apenas incrementa quantidade
            if conta.get(item):
                conta[item] = [conta[item][0] + qtd_item, item, total_item]
            else:
                conta[item] = [qtd_item, item, total_item]
        
        # Imprime itens da conta
        resposta += 'Você pediu:\n'
        for id, item in conta.items():
            if(item[0] > 1): # Verifica plural na resposta
                resposta += '- %s %ss %4.2f \n'%(item[0], item[1], item[2])
            else:
                resposta += '- %s %s %4.2f \n'%(item[0], item[1], item[2])
            
        # Calcula e imprime total da conta
            total_conta = item[0] * item[2]
        resposta += ('Total foi R$ %4.2f \n'%total_conta)
        resposta += 'Qual será a forma de pagamento?\n'

    # Intenção para definir pagamento
    elif pred == 'definir_pagamento':
        resposta += 'Ok, o pagamento será feito com: ' + mensagem + '\n'
        resposta += 'Você quer que seja entregue ou vai vir até o local?'
        pagamento = mensagem

      # Intenção para escolher entrega
    elif pred == 'escolher_entrega':
        resposta += 'Ok, a forma de entrega será: ' + mensagem + '\n'
        entrega = mensagem
    
    # Intenção para dar feedback
    elif pred == 'feedback':
        resposta += 'O seu Feedback é muito importante para nós!\nMuito obrigado pela preferência e Desculpe por qualquer incômodo!\n'
    else:
        resposta = 'Não, entendi. \n'+str_menu(valor_cardapio)

    # Envia no Telegram resposta processada pelo bot
    bot.send_message(mensagem_usuario.chat.id, resposta)      

# Mantém o bot escutando o canal para receber novas mensagens
bot.polling()