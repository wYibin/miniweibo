drop table if exists users;
create table users (
  user_id integer primary key autoincrement,
  user_name text not null,
  email text not null,
  pw_hash text not null
);

drop table if exists messages;
create table messages (
  message_id integer primary key autoincrement,
  user_id integer not null,
  text text not null,
  pub_time integer not null
);

drop table if exists follows;
create table follows (
  follower_id integer not null,
  followed_id integer not null
);
