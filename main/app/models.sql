DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

CREATE FUNCTION create_tsvector(name text, description text, keywords text, body text) RETURNS tsvector AS $$
  BEGIN
  RETURN setweight(to_tsvector(name), 'A')        ||
         setweight(to_tsvector(description), 'B') ||
         setweight(to_tsvector(keywords), 'C')    ||
         setweight(to_tsvector(body), 'D');
  END;
$$ LANGUAGE plpgsql;

CREATE TABLE entries (
  uri character varying(63) PRIMARY KEY,
  name character varying(63) NOT NULL,
  src character varying(10) NOT NULL,
  vector tsvector NOT NULL,
  description text
);

CREATE INDEX vector_index ON entries USING GIN (vector);
