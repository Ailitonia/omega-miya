-- 执行去重 --
DELETE
FROM omega_pixiv_artwork_page
WHERE omega_pixiv_artwork_page.page != 0;

-- 导出去重后数据 --
SELECT
  'pixiv' as origin,
  omega_pixiv_artwork.pid as aid,
  omega_pixiv_artwork.title as title,
  omega_pixiv_artwork.uid as uid,
  omega_pixiv_artwork.uname as uname,
  CASE omega_pixiv_artwork.classified
    WHEN 0 THEN 0
    WHEN 1 THEN 3
    WHEN 2 THEN 1
    ELSE -1
  END as classification,
  CASE omega_pixiv_artwork.nsfw_tag
    WHEN 2 THEN 3
    WHEN 1 THEN 1
    WHEN 0 THEN 0
    ELSE -1
  END as rating,
  omega_pixiv_artwork.width as width,
  omega_pixiv_artwork.height as height,
  omega_pixiv_artwork.tags as tags,
  NULL as description,
  omega_pixiv_artwork.url as source,
  omega_pixiv_artwork_page.original as cover_page,
  omega_pixiv_artwork.created_at as created_at,
  omega_pixiv_artwork.updated_at as updated_at
FROM omega_pixiv_artwork
LEFT JOIN omega_pixiv_artwork_page ON omega_pixiv_artwork.id = omega_pixiv_artwork_page.artwork_index_id
