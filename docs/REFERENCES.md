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

- **Irmischer & Clarke walking speed** (`irmischer_clarke`)
  Irmischer, I. J. & Clarke, K. C. (2018). Measuring and modeling the speed of
  human navigation. *Cartography and Geographic Information Science* 45(2):
  177–186. doi:10.1080/15230406.2017.1292150. — GPS-derived on-path walking
  speed `v = 0.11 + exp(−(G + 5)²/(2·30²))` m/s with the *signed* grade
  `G = slope·100` (%), so the speed peaks on a gentle downhill — anisotropic,
  unlike the `abs()`-symmetrised form in some R implementations.

- **Minetti metabolic cost of transport** (`minetti`)
  Minetti, A. E., Moia, C., Roi, G. S., Susta, D. & Ferretti, G. (2002).
  Energy cost of walking and running at extreme uphill and downhill slopes.
  *Journal of Applied Physiology* 93(3): 1039–1046.
  doi:10.1152/japplphysiol.01177.2001. — Quintic polynomial in the signed
  gradient `i` (J·kg⁻¹·m⁻¹); the cost minimum sits near `i ≈ −0.1`.

- **Pandolf load-carriage metabolic rate** (`pandolf`)
  Pandolf, K. B., Givoni, B. & Goldman, R. F. (1977). Predicting energy
  expenditure with loads while standing or walking very slowly. *Journal of
  Applied Physiology* 43(4): 577–581. doi:10.1152/jappl.1977.43.4.577. — Adds
  body mass, carried load and a terrain factor (threaded from the GUI via
  `cost_params`). For downhill travel the Santee/Yokota correction is applied:
  Santee, W. R., Allison, W. F., Blanchard, L. A. & Small, M. G. (2001). A
  proposed model for load carriage on sloped terrain. *Aviation, Space, and
  Environmental Medicine* 72(6): 562–566; refined in Yokota, M., Berglund,
  L. G., Santee, W. R., Buller, M. J. & Hoyt, R. W. (2004).

- **Multi-criteria composite friction** (`composite_friction`)
  Herzog, I. (2022), as below — proposes slope × hydrological-cost composites;
  Litvine, A. D., Lewis, J. & Starzec, A. W. (2024). A multi-criteria simulation
  of European coastal shipping routes in the 'age of sail'. *Humanities and
  Social Sciences Communications* 11: 412. doi:10.1057/s41599-024-02906-9. —
  Weighting and combining several environmental rasters into one cost surface.
  Itinera builds the composite penalty layer by min-max normalising each input
  and combining by a weighted arithmetic (sum) or geometric (product) mean, with
  per-layer inversion and NoData-as-impassable masks; it then feeds the existing
  `multiplier` / `friction` slots. **Note:** this is a *generic Itinera
  heuristic* combiner — in the spirit of the above, **not** a reproduction of
  their domain-calibrated models — and min-max normalisation makes the composite
  **extent-dependent** (the same input value maps to a different cost under a
  different clip; pre-normalise to fixed ranges for extent-stable results).

- **Wheeled & pack-animal critical-slope costs** (`wheeled`, `pack_animal`) —
  **experimental Itinera heuristics, not calibrated published functions.**
  Verhagen, P., Nuninger, L. & Groenhuijzen, M. R. (2019), as above (a vehicle
  has a critical *upward* slope beyond which movement is impossible), and Herzog
  (2013), as above, supply the *concept* only. The concrete form is an Itinera
  construction: an anisotropic critical-slope cost (uphill threshold tighter than
  downhill), `cost/m = 1 + (uphill/critical_up)² + (downhill/critical_down)²`,
  with **illustrative** preset thresholds for a cart (~8 % critical up) and a
  pack animal (~25 %); no hard cut-off, so steep ground is quadratically (softly)
  impassable. Note Herzog's own vehicle function is *symmetric*, and the
  literature stresses the *absence* of validated pack-animal functions — set the
  thresholds to your own evidence and treat results as exploratory.

- **Accessibility / cost catchment** (`accessibility`)
  Verhagen et al. (2019), as above — "movement potential" surfaces (Llobera's
  total path costs, Mlekuž's potential path fields). — The cost-distance from a
  source *is* an accessibility surface; Itinera derives a catchment (the area
  reachable within a cost budget) and isochrone bands on top of the Dijkstra
  accumulation.

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
  reimplements on the QGIS geostack. The corridor also propagates **cost-model**
  uncertainty: each realisation can sample a cost function from a weighted set
  and jitter its parameters — Herzog, I. (2022), as above, shows there is *no
  universal best* cost model (the globally best model won only 8 of 19 route
  sections), so "which function?" is itself an uncertainty worth propagating.
  The iteration count is backed by an optional **convergence criterion**
  (stabilisation of the corridor, or a target precision — the max per-cell
  *pointwise* Wilson 95 % confidence-interval error on the reported probability;
  pointwise, not a joint guarantee across cells) — the rarely-reported stop rule
  the method needs.

- **Randomized Shortest Paths (RSP)** (`rsp_passages`)
  Panzacchi, M., Van Moorter, B., Strand, O., Saerens, M., Kivimäki, I., St.
  Clair, C. C., Herfindal, I. & Boitani, L. (2015). Predicting the continuum
  between corridors and barriers to animal movements using Step Selection
  Functions and Randomized Shortest Paths. *Journal of Animal Ecology* 85(1):
  32–42. doi:10.1111/1365-2656.12386. — A single inverse-temperature parameter
  θ interpolates between the least-cost path (θ→∞) and the random-walk / circuit
  current density (θ→0); empirical movement is best fit at an *intermediate* θ.
  The RSP formalism (substochastic `W = P_ref ∘ exp(−θ·C)`, fundamental matrix
  `Z = (I−W)⁻¹`, passage `n_i = z_si·z_it/z_st`, free-energy distance) is due to
  Saerens, Kivimäki et al. Exposed in the gdistance R package: van Etten, J.
  (2017). R Package gdistance. *Journal of Statistical Software* 76(13): 1–21.
  doi:10.18637/jss.v076.i13. Itinera computes it numpy/scipy-only over the
  existing asymmetric conductance matrix, so it keeps anisotropy throughout.

## Connectivity / circuit theory

- **Circuit current density & pinch points** (`current_density`)
  McRae, B. H., Dickson, B. G., Keitt, T. H. & Shah, V. B. (2008). Using Circuit
  Theory to Model Connectivity in Ecology, Evolution, and Conservation.
  *Ecology* 89(10): 2712–2724. doi:10.1890/07-1861.1; foundational resistance
  distance in McRae, B. H. (2006). Isolation by Resistance. *Evolution* 60(8):
  1551–1561. doi:10.1111/j.0014-3820.2006.tb00500.x. — Movement as current flow
  over a resistance surface: build the graph Laplacian `L = D − G`, inject unit
  current at the source and ground the target, solve `Lv = i`, and map per-cell
  current density (½·Σ|g(v_i−v_j)|). Pinch points are the high-current cells
  within the least-cost corridor (the Circuitscape "pinchpoint mapper"). Circuit
  theory is undirected, so Itinera symmetrises the conductance — for the
  anisotropic current use the RSP tool at small θ.

- **Barriers / restoration** (`restoration_score`)
  McRae, B. H., Hall, S. A., Beier, P. & Theobald, D. M. (2012). Where to Restore
  Ecological Connectivity? Detecting Barriers and Quantifying Restoration
  Benefits. *PLoS ONE* 7(12): e52604. doi:10.1371/journal.pone.0052604. — A
  moving-window improvement score over the accumulated-cost corridor surfaces:
  for each cell, how much the corridor improves if a strip across the window is
  restored. Itinera vectorises it with `scipy.ndimage.minimum_filter` (no
  per-cell re-solve). Archaeological circuit-connectivity context: Rubio-Campillo
  et al. (2022), doi:10.1007/s10816-022-09549-7; tool landscape: Dutta et al.
  (2022), doi:10.1007/s10980-022-01469-x.

## Uncertainty & validation

- **DEM-error simulation** (`add_dem_error`, `simulate_error_field`)
  Hunter, G. J. & Goodchild, M. F. (1997). Modeling the Uncertainty of Slope and
  Aspect Estimates Derived from Spatial Databases. *Geographical Analysis*
  29(1): 35–49. doi:10.1111/j.1538-4632.1997.tb00944.x. — A
  spatially-autocorrelated error field scaled to a vertical RMSE. **Note:**
  Itinera's generator is an *implementation in the spirit of* this literature,
  **not a reproduction** of a specific method — Hunter & Goodchild use an
  *autoregressive* spatial error model and Lewis (2021) uses *filtered noise +
  sink-fill*, whereas Itinera simulates a chosen **variogram** covariance
  (exponential / spherical / gaussian, with an optional nugget) by FFT spectral
  synthesis (Dietrich & Newsam circulant embedding) — no `gstat` dependency, just
  `scipy.fft`. A fast Gaussian-filter approximation is retained as an option.
  Uncertainty propagation into LCP results follows Lewis (2021), as above.

- **Path Deviation Index (PDI)**
  Jan, O., Horowitz, A. J. & Peng, Z.-R. (2000). Using Global Positioning System
  Data to Understand Variations in Path Choice. *Transportation Research Record*
  1725(1): 37–44. doi:10.3141/1725-06. — Area between a tested and a reference
  line divided by the **straight-line (Euclidean) distance between origin and
  destination** = mean lateral deviation in map units. This is the definition
  used by R `leastcostpath`: the modelled path's endpoints are first snapped to
  the reference O/D, then the area is taken. (An earlier Itinera version divided
  by the reference arc length and mis-attributed PDI to Goodchild & Hunter;
  corrected v0.14.1.) See `core/validation.py` for the method's limitations.

- **Buffer-overlap validation** (`buffer_overlap`)
  Goodchild, M. F. & Hunter, G. J. (1997), as above (the buffer method from the
  same paper). — For each tolerance distance, the share (%) of the modelled
  path's length within that distance of the reference; the metric R
  `leastcostpath` exposes as `buffer_validation`. Computed numpy-only by
  densifying the modelled line and measuring perpendicular distance to the
  reference (no shapely in `core/`). `mean_pairwise_overlap` averages it over a
  set of paths to give the sensitivity tool's route-stability indicator.

## Sensitivity analysis

- **Parameter-variation sensitivity** (Sensitivity analysis algorithm)
  Verhagen, P., Nuninger, L. & Groenhuijzen, M. R. (2019). Modelling of Pathways
  and Movement Networks in Archaeology: An Overview of Current Approaches. In:
  *Finding the Limits of the Limes*, 217–249. Springer.
  doi:10.1007/978-3-030-04576-0_11. — Names sensitivity analysis as a field
  priority. Herzog, I. (2022). Issues in Replication and Stability of Least-cost
  Path Calculations. *Studies in Digital Heritage* 5(2): 131–155.
  doi:10.14434/sdh.v5i2.33796. — Across many route sections the globally best
  cost model was optimal for only some, so a route must be qualified by how
  sensitive it is to the modelling choices. The Itinera tool sweeps cost
  function × connectivity for one O/D pair and reports an agreement surface, a
  per-configuration summary and a route-stability scalar.
