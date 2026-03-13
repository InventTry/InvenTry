create table categories (
	id SERIAL primary key,
	name VARCHAR(50) not null
);

create table attributes (
	id serial primary key,
	category_id integer references categories(id),
	name varchar(50),
	type VARCHAR(3) not null
	constraint chk_type check (type in('num', 'nws', 'txt')),
	suffix VARCHAR(3),
	constraint uq_constraint_id_name unique(category_id, name)
);

create table users (
	id serial primary key,
    email varchar(70) not null unique,
	first_name varchar(50) not null,
	last_name varchar(50) not null,
	password_hash text not null,
	role varchar(20) not null default 'user'
	constraint chk_role check (role in ('admin', 'moderator', 'user')),
	date_joined date not null default current_date,
	date_left date,
	archived boolean not null default false
);

create table inventory (
	id SERIAL primary key,
	display_name VARCHAR(50) not null,
	serial_number text unique,
	date_created date not null default current_date,
    date_updated date not null default current_date,
	category_id integer not null references categories(id),
	assigned_to integer references users(id),
    permissions char(4) not null default 'rw--',
	archived boolean not null default false,
	date_archived date
);

create table user_attribute_values (
	user_id integer references users(id),
	attribute_id integer references attributes(id),
	value text not null,
	primary key (user_id, attribute_id)
);

create table item_attribute_values (
	item_id INTEGER references inventory(id),
	attribute_id INTEGER references attributes(id),
	value TEXT not null,
	primary key (item_id, attribute_id)
);

