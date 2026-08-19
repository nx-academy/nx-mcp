-- New feed entry format: a factual summary of the source (`context`) plus the
-- author's own commentary (`lecture`).
--
-- `content` is deliberately kept and still written to, so that this migration
-- can be applied without coordinating a deployment: nx-academy.github.io keeps
-- reading `content` until it is switched over to `context`. Dropping it is a
-- separate, later migration. Renaming instead would have broken the Astro build
-- and `publish_news` at the very same instant.

ALTER TABLE NewsFeed ADD COLUMN context TEXT;

-- NULL means "entry from the old format", which is meaningful information
-- rather than a gap to backfill. Never give this column a default.
ALTER TABLE NewsFeed ADD COLUMN lecture TEXT;

UPDATE NewsFeed SET context = content WHERE context IS NULL;
