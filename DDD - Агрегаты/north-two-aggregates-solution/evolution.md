# Журнал реализации

Рабочая копия создана из исходного каркаса. Проверки выполнялись Python 3.12.14
командой `python -B -m unittest discover -s tests -v` из корня проекта.
Первоначально обнаружены 7 тестов, все 7 пропущены. Первый запуск этапа 1 из
родительского каталога завершился ошибкой пути `tests`; запуск из корня проекта
исправил ошибку без изменения кода.

## Этап 1 — базовый заказ

- Файлы: `domain/errors.py`, `domain/identifiers.py`, `domain/values.py`, `domain/order.py`, `tests/test_order_baseline.py` (доменные файлы внутри `north_marketplace`).
- Типы: Identifier, OrderId, OrderLineId, BuyerId, Sku, Currency, Quantity, Money, ShippingAddress, OrderStatus, OrderLine, OrderLineSnapshot, Order.
- Команды: временная add_line, change_line_quantity, set_shipping_address, place, cancel.
- Правило: только полный черновик с положительным итогом размещается; валюта едина, после размещения состав и адрес закрыты.
- Успех: размещение, изменение конкретной строки, точный десятичный итог.
- Отказы: InvalidValueError, CurrencyMismatchError, IncompleteOrderError, OrderStateError, OrderLineNotFoundError; состояние сохраняется.
- Проверки: [test_order_baseline.py](tests/test_order_baseline.py), включая неизменяемость значений и старого снимка.
- Результат: 15 тестов, 9 прошли, 6 будущих модулей пропущены.

## Этап 2 — один продавец

- Файлы: identifiers.py, order.py, test_order_baseline.py, test_order_seller.py, model.md.
- Добавлены SellerId, seller_id() и продавец строки; временная add_line принимает продавца.
- Правило: первая успешная строка фиксирует продавца; все последующие принадлежат ему.
- Успех: вторая строка того же продавца. Отказы: SellerMismatchError и DuplicateOrderLineError без изменения состава, суммы и продавца.
- Неудачная первая строка не фиксирует продавца.
- Сохранены все 9 базовых проверок, добавлены 4 в [test_order_seller.py](tests/test_order_seller.py).
- Результат: 18 тестов, 13 прошли, 5 будущих модулей пропущены.

## Этап 3 — подарки

- Файлы: values.py, order.py, все три test_order_*.py, model.md.
- Добавлены LineKind, add_paid_line, add_gift_line; публичная add_line удалена.
- Правило: PAID требует положительную цену, GIFT — нулевую; для place нужна платная часть.
- Успех: книга с подарком, итог не меняется. Отказы: нулевая платная цена, ненулевая цена внутренней подарочной строки (InvalidValueError), только подарки (IncompleteOrderError).
- Сохранены валюта, продавец, уникальность ID, статус и неизменяемые снимки. Проверки прежних этапов переведены на окончательный API без изменения смысла.
- Добавлено 6 сценариев в [test_order_gifts.py](tests/test_order_gifts.py).
- Результат: 23 теста, 19 прошли, 4 будущих модуля пропущены.

## Этап 4 — физический остаток

- Файлы: identifiers.py, values.py, stock_item.py, test_stock_baseline.py, model.md.
- Добавлены StockItemId, WarehouseId, StockBalance и StockItem, receive и write_off.
- Правило: физический остаток неотрицателен; количество действия строго положительно.
- Успех: приход и списание до нуля. Отказ: списание сверх остатка (InsufficientStockError) сохраняет прежний баланс.
- Сохранены все 19 проверок заказа, добавлено 4 в [test_stock_baseline.py](tests/test_stock_baseline.py).
- Результат: 26 тестов, 23 прошли, 3 будущих модуля пропущены.

## Этап 5 — резервы

- Файлы: identifiers.py, values.py, stock_item.py, test_stock_reservations.py, model.md.
- Добавлены ReservationId, ReservationStatus (ACTIVE/RELEASED), StockReservation, ReservationSummary, reserve, release_reservation, active_reserved_quantity.
- ReservationDeadline и проверка часового пояса введены здесь, чтобы reserve сразу имел окончательный типизированный контракт; поведение истечения вводится только на этапе 6.
- Правило: сумма активных резервов не превышает физический остаток. write_off учитывает резервирование.
- Успех: резерв ровно на доступный остаток, освобождение без удаления, несколько резервов.
- Отказы: InsufficientStockError, DuplicateReservationError, ReservationNotFoundError, ReservationStateError; передача Order вместо OrderId даёт InvalidValueError.
- Сохранены 23 предыдущие проверки; добавлено 9 в [test_stock_reservations.py](tests/test_stock_reservations.py).
- Результат: 34 теста, 32 прошли, 2 будущих модуля пропущены.

## Этап 6 — истечение

- Файлы: values.py, stock_item.py, test_stock_expiration.py, model.md.
- Добавлены ReservationDeadline.is_due, EXPIRED, StockItem.expire_reservations и внутренний переход _expire_if_due.
- Правило: ACTIVE со сроком <= now переходит в EXPIRED; физический остаток прежний, завершённые записи не удаляются.
- Успех: прошлый срок, точная граница, смешанная коллекция, эквивалентные моменты разных часовых поясов. Повторная обработка не увеличивает счётчик.
- Отказы: дата без часового пояса (InvalidValueError) до изменений; освобождение истёкшего резерва (ReservationStateError).
- Сохранены 32 предыдущие проверки, добавлено 7 в [test_stock_expiration.py](tests/test_stock_expiration.py).
- Результат доменной части: 40 тестов, 39 прошли, только демонстрация ещё пропущена.

## Итоговый сценарий и проверка контракта

- Реализованы run_demo() и main(); test_demo.py содержит 5 проверок, включая запуск отдельного процесса CLI, детерминированность и порядок place → reserve.
- После сборки сценария: 44 теста прошли, пропусков нет. Вывод: order-100, PLACED, 1290.00 RUB, остатки 8 и 7, резервирование по OrderId.
- При финальной сверке добавлены два изолированных негативных случая: пустой заказ с корректным адресом и пустое название первой строки. Первый защищает условие непустого состава независимо от адреса, второй — отсутствие частичной фиксации продавца.
- Общая примесь неизменяемости не содержит заглушек; все конкретные значения явно определяют состав для равенства.

## Финальная проверка для сдачи

- Среда: CPython 3.12.14, uv 0.13.8, macOS ARM64.
- uv установлен во временный каталог для проверки; зависимостей в проект не добавлено.
- Создано новое изолированное окружение вне сдаваемой папки. uv запущен с `--offline`, явно указанным Python 3.12 и запретом загрузки интерпретатора.
- `uv run python -B -m unittest discover -s tests -v`: **46 тестов, OK, 0 пропусков**.
- `uv run python -B -m north_marketplace`: код завершения 0, требуемые order-100 / PLACED / 1290.00 RUB / 8 / 7 и сообщение о резервировании по OrderId.
- Поиск по исходникам и тестам не обнаружил TODO, NotImplementedError, skip, self.fail, @property, @dataclass или Protocol.
- README описывает основной запуск через uv и запуск обычным Python 3.11+; model.md содержит итоговые композиции, состояния и последовательность вызовов; uv.lock фиксирует проект без зависимостей.
- Исходный каркас не изменялся. В сдаваемый архив включены только проект, тесты и документация; окружения и кеши исключены.
