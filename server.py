from flask import Flask, request
import logging
import random
import json


# Инициализация приложения и логирования:
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


# Создаем словарь, в котором ключ — название города, а значение — массив,
# где перечислены ID картинок, которые мы записали в прошлом пункте:
cities = {
    'москва': ['1540737/daa6e420d33102bf6947',
               '213044/7df73ae4cc715175059e'],
    'париж': ["1652229/f77136c2364eb90a3ea8",
              '3450494/aca7ed7acefde22341bdc'],
    'нью-йорк': ['1652229/728d5c86707054d4745f',
                 '1030494/aca7ed7acefde2606bdc'],
}

# Создаём словарь, где для каждого пользователя мы будем хранить его имя:
sessionStorage = {}


# Обработка полученной информации с помощью метода POST:
@app.route('/post', methods=['POST'])
def main():
    # Получаем данные в формате JSON:
    logging.info('Request: %r', request.json)

    # Данные перед началом игры:
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    # Начинаем игру, логируем данные:
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return json.dumps(response)


# Обрабатываем диалог с пользователем:
def handle_dialog(res, req):
    # ID пользователя, приветственное сообщение
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Добро пожаловать в игру! Как вас зовут?'
        sessionStorage[user_id] = {
            'first_name': None,  # Имя пользователя
            'game_started': False  # Начал ли пользователь игру
        }
        return

    # Если пользователь не назвал своё имя - сообщаем об этом:
    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)

        if first_name is None:
            res['response']['text'] = 'Вы не назвали своё имя! Пожалуйста, скажите, как вас зовут?'
        else:

            sessionStorage[user_id]['first_name'] = first_name
            # Создание массива, в котором будут храниться угаданные города:
            sessionStorage[user_id]['guessed_cities'] = []

            # Предлагаем сыграть:
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Отгадаете город по фото?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                }
            ]
    else:
        # Если мы получили имя пользователя, то обрабатываем его ответ на предыдущий вопрос.
        # В sessionStorage[user_id]['game_started'] хранится True или False в зависимости
        # от того, начал пользователь игру или нет:
        if not sessionStorage[user_id]['game_started']:

            # Если игра не начата, то ожидаем ответ на предложение сыграть:
            if 'да' in req['request']['nlu']['tokens']:

                # Если пользователь согласился, то проверяем, не отгадал ли он уже все города...
                # По схеме можно увидеть, что здесь окажутся и пользователи, которые уже отгадывали города:
                if len(sessionStorage[user_id]['guessed_cities']) == 3:

                    # Если все три города отгаданы, то заканчиваем игру
                    res['response']['text'] = 'Вы отгадали все города!'
                    res['end_session'] = True

                else:
                    # Если есть неотгаданные города, то продолжаем игру:
                    sessionStorage[user_id]['game_started'] = True

                    # Номер попытки, чтобы показывать фото по порядку:
                    sessionStorage[user_id]['attempt'] = 1

                    # Функция, которая выбирает город для игры и показывает фото:
                    play_game(res, req)

            # Обрабатываем ответы "НЕТ" и неправильные ответы, которые Алиса не может обработать:
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Если передумаете - я буду рядом!'
                res['end_session'] = True

            else:
                res['response']['text'] = 'Мне нужен точный ответ! Будете играть - ДА, или же НЕТ?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    }
                ]
        else:
            # Начинаем игру:
            play_game(res, req)


# Функция для игры:
def play_game(res, req):

    # Получаем USERID, количество попыток ATTEMPT:
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']

    # Если попытка - первая, то случайным образом выбираем город для угадывания:
    if attempt == 1:
        city = random.choice(list(cities))

        # Выбираем его до тех пор, пока не выберем город, которого нет в sessionStorage[user_id]['guessed_cities']:
        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities))

        # Записываем город в информацию о пользователе:
        sessionStorage[user_id]['city'] = city

        # Добавляем в ответ картинку:
        res['response']['card'] = {}
        res['response']['card']['image_id'] = cities[city][attempt - 1]
        res['response']['card']['title'] = 'Хм... что же это за город?'
        res['response']['card']['type'] = 'BigImage'
        res['response']['text'] = 'Будем играть!'

    else:
        # Если попытка уже не первая:
        city = sessionStorage[user_id]['city']

        # Проверяем есть ли правильный ответ в сообщении пользователя.
        # Если да, то добавляем город к sessionStorage[user_id]['guessed_cities']
        # и отправляем пользователя на второй круг:
        if get_city(req) == city:
            res['response']['text'] = 'Правильно! Сыграем ещё?'
            sessionStorage[user_id]['guessed_cities'].append(city)
            sessionStorage[user_id]['game_started'] = False
            return

        else:
            # Если попытка третья, то значит, что все картинки уже показаны. В этом случае отвечаем пользователю,
            # добавляем город к sessionStorage[user_id]['guessed_cities'] и отправляем его на второй круг:
            if attempt == 3:
                res['response']['text'] = (f'Эх... ну, вы попытались, ничего страшного. Это город: {city.title()}. '
                                           f'Сыграем ещё?')
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed_cities'].append(city)
                return

            # В противном случае - показываем следующую картинку:
            else:
                res['response']['card'] = {}
                res['response']['card']['title'] = 'Ответ неверный... Держите следующую фотографию!'
                res['response']['card']['image_id'] = cities[city][attempt - 1]
                res['response']['card']['type'] = 'BigImage'
                res['response']['text'] = 'Вы не угадали!'

    # Увеличиваем количество попыток:
    sessionStorage[user_id]['attempt'] += 1


# Получаем город:
def get_city(req):
    # Перебираем именованные сущности:
    for entity in req['request']['nlu']['entities']:

        # Если тип сущности - YANDEX.GEO, то пытаемся получить город(city), а если нет, то возвращаем None:
        if entity['type'] == 'YANDEX.GEO':

            # Возвращаем None, если мы не смогли найти сущности с типом YANDEX.GEO:
            return entity['value'].get('city', None)


# Первая игра:
def get_first_name(req):
    # Перебираем сущности:
    for entity in req['request']['nlu']['entities']:

        # Находим сущность с типом 'YANDEX.FIO':
        if entity['type'] == 'YANDEX.FIO':

            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None:
            return entity['value'].get('first_name', None)


# Запуск приложения
if __name__ == '__main__':
    app.run()