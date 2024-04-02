--select * from legende left join(
select id,
round(avg(band_1),0) r,
round(avg(band_2),0) g,
round(avg(band_3),0) b
from sampled_points
group by id
 --using(id)
 
 --qgis symbology expression
 --"r"||','||"g"||','||"b"||',255'