# References

Literature behind the methods implemented in Itinera. BibTeX entries for all of
these are in [`references.bib`](references.bib).

## Cost functions

- **Tobler's Hiking Function** (`tobler`, `tobler_offpath`)
  Tobler, W. (1993). *Three Presentations on Geographical Analysis and Modeling.*
  National Center for Geographic Information and Analysis, Technical Report 93-1.
  Santa Barbara. — Walking speed `v = 6·exp(−3.5·|S + 0.05|)` km/h; the +0.05
  offset puts maximum speed on a gentle downhill, making it directional.

- **Naismith's rule** (`naismith`)
  Naismith, W. W. (1892). Cruach Ardran, Stobinian, and Ben More.
  *Scottish Mountaineering Club Journal* 2(3): 136. — Base walking pace plus a
  fixed time penalty per unit of ascent.

- **Herzog metabolic cost** (`herzog`)
  Herzog, I. (2013). Theory and Practice of Cost Functions. In: Contreras, F.,
  Farjas, M. & Melero, F. J. (eds), *Fusion of Cultures. Proceedings of the 38th
  Annual Conference on Computer Applications and Quantitative Methods in
  Archaeology (CAA), Granada 2010*, 375–382. BAR International Series 2494.
  Oxford: Archaeopress. — Sixth-order polynomial in slope, normalised to ~1 on
  the flat.

- **Llobera & Sluckin metabolic energy** (`llobera_sluckin`)
  Llobera, M. & Sluckin, T. J. (2007). Zigzagging: Theoretical insights on
  climbing strategies. *Journal of Theoretical Biology* 249(2): 206–217.
  doi:10.1016/j.jtbi.2007.07.020. — Energy expenditure as a function of slope;
  note its descent term makes downhill the costlier direction at moderate
  gradients (see `tests/test_cost_functions.py`).

## Path & corridor methods

- **From-Everywhere-To-Everywhere (FETE)**
  White, D. A. & Barber, S. B. (2012). Geospatial modeling of pedestrian
  transportation networks: a case study from precolumbian Oaxaca, Mexico.
  *Journal of Archaeological Science* 39(8): 2684–2696.
  doi:10.1016/j.jas.2012.04.017. — Accumulated traversal frequency over all
  pairwise least-cost paths reveals terrain-driven movement corridors.

- **Least-cost corridor (LCC)**
  The corridor surface is the sum of two accumulated-cost surfaces (one grown
  from the origin, one from the destination on the reversed graph); cells near
  the minimum delineate a band of near-optimal routes. For methodological
  background and caveats see Herzog, I. (2014). *Least-cost Paths — Some
  Methodological Issues.* Internet Archaeology 36. doi:10.11141/ia.36.5.

- **Stochastic / probabilistic LCP**
  Lewis, J. (2021). Probabilistic Modelling for Incorporating Uncertainty in
  Least Cost Path Results: a Postdictive Roman Road Case Study. *Journal of
  Archaeological Method and Theory* 28: 911–924.
  doi:10.1007/s10816-021-09522-w. — Monte-Carlo propagation of DEM error into a
  probabilistic corridor. Implemented here as `core/stochastic.py`; see also the
  `leastcostpath` R package (Lewis, J., CRAN/GitHub) whose ideas Itinera
  reimplements on the QGIS geostack.

## Uncertainty & validation

- **DEM-error simulation** (`add_dem_error`)
  Hunter, G. J. & Goodchild, M. F. (1997). Modeling the Uncertainty of Slope and
  Aspect Estimates Derived from Spatial Databases. *Geographical Analysis*
  29(1): 35–49. doi:10.1111/j.1538-4632.1997.tb00944.x. — Basis for adding a
  spatially-autocorrelated error field scaled to a vertical RMSE. Itinera
  approximates the spatial autocorrelation with a Gaussian filter (no variogram
  dependency).

- **Path Deviation Index (PDI)**
  Goodchild, M. F. & Hunter, G. J. (1997). A simple positional accuracy measure
  for linear features. *International Journal of Geographical Information
  Science* 11(3): 299–306. doi:10.1080/136588197242419. — Area between a tested
  and a reference line divided by the reference length = mean deviation in map
  units. See `core/validation.py` for the method's limitations.
