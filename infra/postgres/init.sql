-- infra/postgres/init.sql
-- Faz 1 — PostgreSQL başlangıç konfigürasyonu
-- Docker Compose bu dosyayı ilk çalıştırmada otomatik yükler

-- Uygulama session değişkeni için gerekli uzantılar
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- RLS'in SET LOCAL ile çalışabilmesi için uygulama kullanıcısına izin
-- (superuser değil, sınırlı yetkili uygulama kullanıcısı)
ALTER ROLE membro_user SET app.current_tenant_id TO '';
