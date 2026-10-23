# Модель данных

Модели SQLAlchemy — в [`backend/app/models/`](../backend/app/models/), миграции — в [`backend/alembic/versions/`](../backend/alembic/versions/).
Все первичные ключи — UUID (кроме продукта: у него постоянный код). Деньги — `NUMERIC(16,2)`.

```mermaid
erDiagram
    COMPANIES ||--o{ USERS : "представители"
    COMPANIES ||--o{ APPLICATIONS : "подаёт"
    USERS ||--o{ APPLICATIONS : "автор"
    PRODUCTS ||--o{ APPLICATIONS : "продукт"
    APPLICATIONS ||--o{ APPLICATION_EVENTS : "история"
    APPLICATIONS ||--o{ EXTERNAL_CHECKS : "проверки"
    APPLICATIONS ||--o{ SCORING_RESULTS : "скоринг"
    APPLICATIONS ||--o{ OFFERS : "предложения"
    APPLICATIONS ||--o{ INFO_REQUESTS : "запросы уточнений"
    APPLICATIONS ||--o{ DOCUMENTS : "файлы"
    USERS ||--o{ APPLICATION_EVENTS : "кто действовал"

    COMPANIES {
        uuid id PK
        string inn UK "ИНН, 10 или 12 цифр"
        string ogrn "ОГРН / ОГРНИП"
        string company_type "LLC (ООО) / IE (ИП)"
        string name
        string okved "основной ОКВЭД"
        string industry "отрасль простыми словами"
        date registration_date
        string region
        numeric annual_revenue "null — нет отчётности"
        int employees_count
    }
    USERS {
        uuid id PK
        string login UK
        string password_hash "bcrypt"
        string full_name
        string role "client / employee"
        uuid company_id FK "только у клиента"
        string position "должность в компании"
        bool is_active
    }
    PRODUCTS {
        string code PK
        string name
        text description
        text suitable_for "для чего подходит"
        json purposes "коды целей"
        numeric min_amount
        numeric max_amount
        int min_term_months
        int max_term_months
        numeric base_rate "% годовых"
        bool requires_collateral
        int decision_days
        json required_fields
        int sort_order
        bool is_active
    }
    APPLICATIONS {
        uuid id PK
        int number UK "№ для людей, с 1001"
        uuid company_id FK
        uuid author_id FK
        string product_code FK
        numeric amount
        int term_months
        string purpose_code
        text purpose_comment
        text collateral_description
        numeric monthly_revenue
        numeric monthly_expenses
        numeric current_loan_payments
        string status
        int version "оптимистичная блокировка"
        timestamp created_at
        timestamp updated_at
        timestamp submitted_at
        timestamp decided_at
    }
    APPLICATION_EVENTS {
        uuid id PK
        uuid application_id FK
        string from_status "null — создание"
        string to_status
        string action
        string actor_type "client / employee / system"
        uuid actor_user_id FK
        text comment "видит клиент"
        json payload "детали для сотрудника"
        timestamp created_at
    }
    EXTERNAL_CHECKS {
        uuid id PK
        uuid application_id FK
        string check_type "egrul / bki"
        string status "ok / error / timeout"
        json request
        json response
        text error_message
        int attempts
        int duration_ms
        timestamp created_at
    }
    SCORING_RESULTS {
        uuid id PK
        uuid application_id FK
        int total_score
        int max_score
        string grade "A–E"
        json factors "вклад каждого фактора"
        numeric debt_to_income
        string rules_version
        timestamp created_at
    }
    OFFERS {
        uuid id PK
        uuid application_id FK
        string offer_type "as_requested / counter_offer"
        numeric amount
        int term_months
        numeric rate
        numeric monthly_payment
        timestamp valid_until
        string status "active / accepted / declined / superseded"
        uuid created_by_user_id FK "null — система"
        timestamp created_at
    }
    INFO_REQUESTS {
        uuid id PK
        uuid application_id FK
        json requested_fields
        json requested_documents
        text comment
        string created_by_type "system / employee"
        uuid created_by_user_id FK
        bool is_open
        text response_comment
        timestamp responded_at
    }
    DOCUMENTS {
        uuid id PK
        uuid application_id FK
        uuid uploaded_by_user_id FK "null — сформирован системой"
        string kind "вид документа"
        string original_filename "очищенное имя"
        string stored_path "путь в UPLOAD_DIR"
        string content_type
        int size_bytes
        timestamp created_at
    }
```

## Пояснения

- **`applications.version`** увеличивается при каждом изменении (SQLAlchemy `version_id_col`). Клиент может передать
  `version` в `PATCH` и в действиях — если заявку уже изменили, получит 409.
- **`application_events`** — одновременно аудит (кто, когда, из какого статуса в какой, с какими деталями) и таймлайн для клиента.
  `comment` показывается клиенту, `payload` (коды причин решения, статусы проверок, условия предложения) — только сотруднику.
- **Повторная обработка** (после `provide_info`) создаёт новые записи `external_checks` и `scoring_results`;
  карточка сотрудника показывает последние. Новые предложения помечают старые как `superseded`.
- **Продукты** синхронизируются из `config/products.yaml` при каждом старте; удалённый из конфига продукт становится `is_active = false`.
- **Файлы документов** лежат в volume `uploads` (`UPLOAD_DIR/<id заявки>/<случайное имя>`), в БД — только метаданные.
