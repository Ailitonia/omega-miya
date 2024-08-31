-- 执行去重 --
DELETE
FROM omega_pixiv_artwork_page
WHERE omega_pixiv_artwork_page.page != 0;

-- 导出去重后数据 --
SELECT
  'pixiv' AS origin,
  omega_pixiv_artwork.pid AS aid,
  omega_pixiv_artwork.title AS title,
  omega_pixiv_artwork.uid AS uid,
  omega_pixiv_artwork.uname AS uname,
  CASE omega_pixiv_artwork.classified
    WHEN 0 THEN 0
    WHEN 1 THEN 3
    WHEN 2 THEN 1
    ELSE -1
  END AS classification,
  CASE omega_pixiv_artwork.nsfw_tag
    WHEN 2 THEN 3
    WHEN 1 THEN 1
    WHEN 0 THEN 0
    ELSE -1
  END AS rating,
  omega_pixiv_artwork.width AS width,
  omega_pixiv_artwork.height AS height,
  omega_pixiv_artwork.tags AS tags,
  NULL AS description,
  omega_pixiv_artwork.url AS source,
  omega_pixiv_artwork_page.original AS cover_page,
  omega_pixiv_artwork.created_at AS created_at,
  omega_pixiv_artwork.updated_at AS updated_at
FROM omega_pixiv_artwork
LEFT JOIN omega_pixiv_artwork_page ON omega_pixiv_artwork.id = omega_pixiv_artwork_page.artwork_index_id
