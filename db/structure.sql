create table if not exists watchlist (
    id serial primary key,
    enable boolean not null default true,
    url varchar(2048) not null,
    content_rx varchar(2048),
    interval integer not null,
    last_start timestamp,
    last_end timestamp
);

create table if not exists check_log (
    wl_id int constraint fk_watchlist references watchlist (id) on delete cascade,
    "start" timestamp not null,
    "end" timestamp,
    "connect" int,
    ttfb int,
    response int,
    status_code int,
    content_check boolean,
    error_message varchar,
    constraint pk_check_log primary key (wl_id, "start")
);
