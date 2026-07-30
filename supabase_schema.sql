-- CineRoulette - Supabase Tablo Kurulumu
-- Bunu Supabase panelinde "SQL Editor" sekmesine yapıştırıp çalıştır.

create table if not exists favorites (
    session_id text not null,
    content_id bigint not null,
    content jsonb not null,
    created_at timestamptz default now(),
    primary key (session_id, content_id)
);

create table if not exists feedback (
    session_id text not null,
    content_id bigint not null,
    status text not null check (status in ('watched', 'disliked')),
    content jsonb not null,
    marked_at timestamptz default now(),
    primary key (session_id, content_id)
);

-- Oturum bazlı sorguları hızlandırmak için indeksler
create index if not exists idx_favorites_session on favorites (session_id);
create index if not exists idx_feedback_session on feedback (session_id);