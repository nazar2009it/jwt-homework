# JWT и проверка возраста

Третье домашнее задание: добавить дату рождения в пользовательскую модель и JWT,
а при создании товара разрешать действие только с 18 лет.

Проект продолжает CustomUser и CustomPermissions из предыдущих заданий.
Модель пользователя называется `users.User` и подключена через `AUTH_USER_MODEL`.

## Что сделано

- `birthdate` — необязательное поле даты рождения. Формат API: `YYYY-MM-DD`.
- Регистрация и вход возвращают JWT `access`, `refresh` и данные пользователя.
- Дата рождения включается в оба токена строкой или `null`.
- API использует `Authorization: Bearer <access>`.
- `common/validators.py` проверяет возраст по `birthdate` из проверенного JWT.
- Проверка вызывается в `ProductViewSet.perform_create` перед сохранением товара.
- JWT проверяется Simple JWT, включая подпись, срок действия и тип токена.
- Сохраняются правила второго ДЗ: обычный пользователь работает со своими товарами,
  модератор (`is_staff=True`) может работать со всеми товарами, но не создавать их.

## Правила создания товара

| Пользователь | POST /api/v1/products/ |
| --- | --- |
| Без JWT | 401 |
| Обычный пользователь, 18 лет и старше | 201 |
| Обычный пользователь младше 18 лет | 400 с сообщением о возрасте |
| Обычный пользователь без birthdate в токене | 400 с просьбой указать дату |
| Модератор или суперпользователь | 403 по правилу второго ДЗ |

Сообщения:

```json
{"birthdate": "Вам должно быть 18 лет, чтобы создать продукт."}
```

```json
{"birthdate": "Укажите дату рождения, чтобы создать продукт."}
```

Ровно в день 18-летия создание разрешено. Возраст считается по текущей дате
в часовом поясе проекта (`Asia/Bishkek`), с учётом месяца и дня рождения.
Для родившихся 29 февраля в невисокосном году граница наступает 1 марта.

GET, PUT, PATCH и DELETE не требуют совершеннолетия; применяются права владельца
и модератора. Дата рождения, переданная в теле запроса товара, не участвует в проверке.

## Основные файлы

- `users/models.py` — модель пользователя с `birthdate`.
- `users/migrations/0002_user_birthdate.py` — миграция нового поля.
- `users/serializers.py` — регистрация и `LoginSerializer.get_token` с JWT claim.
- `common/validators.py` — валидация даты и проверка возраста.
- `products/views.py` — вызов проверки перед созданием товара.
- `products/permissions.py` — права модератора и владельца.
- `config/settings.py` — JWTAuthentication, сроки токенов и Swagger.

## Установка и запуск в PowerShell

Открой терминал в папке с `manage.py`. Каждую команду выполняй отдельно.

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" -m venv .venv
```

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```powershell
.\.venv\Scripts\python.exe manage.py test common users products
```

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

На вопросы команды введи email, телефон и два раза одинаковый пароль.
После завершения вводи следующую команду:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Swagger: http://127.0.0.1:8000/swagger/
Админка: http://127.0.0.1:8000/admin/

Для Linux/macOS используй `python3 -m venv .venv`, затем
`.venv/bin/python` вместо `.\.venv\Scripts\python.exe`.

Если окружение первого ДЗ уже установлено, можно использовать его Python
из терминала нового проекта, предварительно установив этот `requirements.txt`.
Третьему ДЗ дополнительно нужен пакет `djangorestframework-simplejwt`.

## Эндпоинты

| Метод | URL | Действие |
| --- | --- | --- |
| POST | /api/v1/auth/register/ | Регистрация и пара JWT |
| POST | /api/v1/auth/login/ | Вход по email и паролю |
| POST | /api/v1/auth/token/refresh/ | Новый access по refresh |
| GET | /api/v1/auth/me/ | Текущий пользователь |
| GET, POST | /api/v1/products/ | Список своих товаров, создание |
| GET, PUT, PATCH, DELETE | /api/v1/products/<id>/ | Работа с товаром |
| GET | /api/schema/ | OpenAPI |
| GET | /swagger/ | Swagger UI |

Пример регистрации:

```json
{
  "email": "student@example.com",
  "password": "StudyPassword!2026",
  "password_confirm": "StudyPassword!2026",
  "birthdate": "2000-01-01"
}
```

Пример ответа (токены сокращены):

```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 1,
    "email": "student@example.com",
    "phone_number": "",
    "birthdate": "2000-01-01",
    "is_staff": false,
    "is_superuser": false
  }
}
```

В Swagger нажми Authorize и вставь access-токен в поле JWT.
Для ручного HTTP-запроса используй заголовок `Authorization: Bearer <access>`.

Пример товара:

```json
{"title": "Учебник", "description": "Хорошее состояние", "price": "100.00"}
```

Пример обновления токена:

```json
{"refresh": "eyJ..."}
```

Access действует 15 минут, refresh — 1 день. Обновление access сохраняет дату
из refresh. Если изменить birthdate через админку, нужно снова войти, чтобы получить
новые токены с новой датой. Старые JWT сохраняют прежний claim до истечения срока.

Публичный API `me` только читает профиль. Birthdate можно указать при регистрации
или изменить через админку. Дату в будущем сохранить через регистрацию/формы нельзя.

## Тесты

В проект включены 82 теста: регистрация, вход, JWT, обновление токенов, срок действия,
подмена подписи, дата рождения, граница 18-летия, отсутствие даты, источник даты
из токена, CRUD и права модератора. Результат выполненных проверок — в `VALIDATION.md`.

## Отдельный репозиторий GitHub

Создай пустой репозиторий `jwt-homework` в GitHub, без автоматически добавленных
README, .gitignore и лицензии. Из папки с manage.py выполни:

```powershell
git init -b main
git config user.name "Nazar"
git config user.email "ratbratbekovnazar@gmail.com"
git add .
git commit -m "Add JWT birthdate and product age validation"
git remote add origin https://github.com/nazar2009it/jwt-homework.git
git push -u origin main
```

Виртуальное окружение, SQLite и локальные настройки исключены через .gitignore.
