-- `slug` already exists and is already populated by `slugify_title()`, so this
-- migration only enforces uniqueness. Existing slugs are left untouched on
-- purpose: they are public anchors (`/feed#<slug>`, see News.astro).

-- Defensive: `slug` is NOT NULL, but nothing stops an empty string.
UPDATE NewsFeed SET slug = 'news-' || id WHERE slug IS NULL OR trim(slug) = '';

-- Only duplicates are rewritten, and the oldest row of each group keeps its
-- slug, so no anchor that has ever been shared breaks. Suffixing with `id`
-- makes the result unique and the statement replayable: a row that has already
-- been suffixed forms its own group, becomes its own MIN(id), and is skipped.
UPDATE NewsFeed
SET slug = slug || '-' || id
WHERE id NOT IN (SELECT MIN(id) FROM NewsFeed GROUP BY slug);

CREATE UNIQUE INDEX IF NOT EXISTS idx_newsfeed_slug ON NewsFeed(slug);
