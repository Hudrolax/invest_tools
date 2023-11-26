CREATE TABLE IF NOT EXISTS public.users
(
    "id" serial PRIMARY KEY,
    "name" character varying(50),
    "telegram_id" bigint,
    "email" character varying(100)
);
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_email ON users(email);


CREATE TABLE IF NOT EXISTS public.brokers
(
    "id" serial PRIMARY KEY,
    "name" character varying(50) NOT NULL
);


CREATE TABLE IF NOT EXISTS public.symbols
(
    "id" serial PRIMARY KEY,
    "name" character varying(10),
    "broker_id" integer NOT NULL,
    FOREIGN KEY (broker_id) REFERENCES brokers(id) ON DELETE CASCADE,
    UNIQUE ("name", "broker_id")
);
CREATE INDEX idx_symbols_name ON symbols(name);


CREATE TABLE IF NOT EXISTS public.alerts
(
    "id" serial PRIMARY KEY,
    "symbol_id" integer NOT NULL,
    "price" numeric(18, 10) NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "triggered_at" timestamp with time zone,
    "trigger" character varying(20) NOT NULL,
    "is_active" boolean NOT NULL DEFAULT FALSE,
    "triggered" boolean NOT NULL DEFAULT FALSE,
    "user_id" integer NOT NULL,
    "is_sent" boolean NOT NULL DEFAULT FALSE,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_alerts_symbol ON alerts(symbol_id);
CREATE INDEX idx_alerts_user ON alerts(user_id);