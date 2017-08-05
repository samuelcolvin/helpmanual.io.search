DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

CREATE TABLE entries (
  uri character varying(63) PRIMARY KEY,
  name character varying(63) NOT NULL,
  src character varying(20) NOT NULL,
  vector tsvector NOT NULL,
  description text,
  keywords text,
  body text
);

CREATE INDEX vector_index ON entries USING GIN (vector);


CREATE FUNCTION create_tsvector() RETURNS trigger AS $create_tsvector$
  BEGIN
  NEW.vector :=  setweight(to_tsvector(NEW.name), 'A')        ||
                 setweight(to_tsvector(NEW.description), 'B') ||
                 setweight(to_tsvector(NEW.keywords), 'C')    ||
                 setweight(to_tsvector(NEW.body), 'D');
  NEW.keywords := NULL;
  NEW.body := NULL;
  return NEW;
  END;
$create_tsvector$ LANGUAGE plpgsql;

CREATE TRIGGER create_tsvector BEFORE INSERT OR UPDATE ON entries
    FOR EACH ROW EXECUTE PROCEDURE create_tsvector();
