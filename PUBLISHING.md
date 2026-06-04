# Publishing to the QGIS Plugin Repository

Steps to submit **Itinera – Least-Cost Pathways** to
[plugins.qgis.org](https://plugins.qgis.org).

## 1. Create an OSGeo ID (one-time)

The QGIS plugin repository authenticates against OSGeo LDAP. Create an account
(if you don't have one) at:

- <https://id.osgeo.org/ldap/create>

Then you can sign in at <https://plugins.qgis.org> with those credentials.

## 2. Pre-flight checklist

- [ ] `metadata.txt` is complete: `name`, `qgisMinimumVersion`, `description`,
      `about`, `version`, `author`, `email`, `repository`, `tracker`,
      `homepage`, `tags`, `category`, `icon`, `experimental`,
      `hasProcessingProvider`. (All set in this repo.)
- [ ] `version` in `metadata.txt` matches the git tag and the top
      `CHANGELOG.md` entry. `metadata.txt` is the single source of truth.
- [ ] `LICENSE` present (MIT).
- [ ] `__init__.py` exposes `classFactory(iface)`.
- [ ] Tests green: `pip install -r requirements-dev.txt && pytest`.
- [ ] Syntax clean: `python3 -m py_compile core/*.py algorithms/*.py gui/*.py
      provider.py plugin.py __init__.py`.

## 3. Build the upload zip

The repository root **is** the plugin folder (`itinera/`). The QGIS validator
requires the zip to contain exactly one top-level directory whose name is the
plugin's package name (`itinera`). Build it from the parent directory:

```bash
cd ..
VERSION=$(sed -n 's/^version=//p' itinera/metadata.txt)
zip -r "itinera-$VERSION.zip" itinera \
    -x 'itinera/.git/*' \
       'itinera/.github/*' \
       'itinera/tests/*' \
       'itinera/*/__pycache__/*' \
       'itinera/__pycache__/*' \
       '*.pyc' \
       'itinera/.pytest_cache/*' \
       'itinera/.venv/*'
```

The dev-only files (`tests/`, `.github/`, caches) are excluded to keep the
package lean — they are not needed at runtime. `metadata.txt` and `__init__.py`
must remain inside `itinera/`.

Verify the structure:

```bash
unzip -l "itinera-$VERSION.zip" | head    # must show itinera/metadata.txt etc.
```

## 4. Upload

1. Sign in at <https://plugins.qgis.org> with your OSGeo ID.
2. Go to **Plugins → Upload a plugin** (<https://plugins.qgis.org/plugins/add/>).
3. Upload the `itinera-$VERSION.zip` built above.
4. The first version of a new plugin is reviewed/approved by the QGIS plugin
   maintainers before it appears publicly. Because `experimental=True`, users
   must tick *"Show also experimental plugins"* in the QGIS Plugin Manager
   settings to see and install it.

## 5. Subsequent releases

1. Bump `version=` in `metadata.txt` and add a `CHANGELOG.md` entry.
2. Tag: `git tag vX.Y.Z && git push --tags`.
3. Rebuild the zip and upload it as a new version (same plugin page).
