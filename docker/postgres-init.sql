-- Runs once when the Postgres volume is created: separate database for the test suite,
-- so running the integration tests never wipes your local dev data.
CREATE DATABASE padel_test;
