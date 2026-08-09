/* ============================================================
   ART-DECO DIAMOND MOSAIC — tile generator
   ============================================================
   Fills every .deco-mosaic with enough tiles to cover its box once the
   field is rotated 45deg, and tags each tile with the motif class its
   row/column position calls for.

   The count has to be computed rather than authored: a field rotated
   45deg inside a W x H box needs a square of side (W + H) / sqrt(2) to
   reach all four corners, so the right number of tiles depends on the
   panel's measured size and cannot be written into the markup. */
(function () {
    'use strict';

    const ROOT2 = Math.SQRT2;

    function readPx(styles, name, fallback) {
        const n = parseFloat(styles.getPropertyValue(name));
        return Number.isFinite(n) && n > 0 ? n : fallback;
    }

    /* The deco trellis: two crossing diagonal runs with a stud at their
       intersections. Driven by row/col so the geometry survives a resize. */
    function motifFor(row, col) {
        const down = (row + col) % 8;
        const up = (row - col + 800) % 8;
        if (down === 0 && up === 0) return 'is-lit';
        if (down === 0 || up === 0) return 'is-brass';
        if (row % 4 === 0 && col % 4 === 0) return 'is-lit';
        return '';
    }

    function build(host) {
        const rect = host.getBoundingClientRect();
        if (!rect.width || !rect.height) return;

        const styles = getComputedStyle(host);
        const tile = readPx(styles, '--tile', 34);
        const grout = readPx(styles, '--grout', 2);
        const pitch = tile + grout;

        // Side of the square that still covers the box after a 45deg turn.
        const span = (rect.width + rect.height) / ROOT2;
        const count = Math.ceil(span / pitch) + 2;

        // Nothing to do if the panel still needs the same grid.
        if (host.dataset.decoCount === String(count)) return;
        host.dataset.decoCount = String(count);

        const field = document.createElement('div');
        field.className = 'deco-mosaic-field';
        field.setAttribute('aria-hidden', 'true');
        field.style.setProperty('--cols', String(count));

        const frag = document.createDocumentFragment();
        for (let row = 0; row < count; row++) {
            for (let col = 0; col < count; col++) {
                const cell = document.createElement('span');
                const motif = motifFor(row, col);
                cell.className = motif ? 'deco-tile ' + motif : 'deco-tile';
                frag.appendChild(cell);
            }
        }
        field.appendChild(frag);

        const previous = host.querySelector('.deco-mosaic-field');
        if (previous) previous.remove();
        host.appendChild(field);
    }

    function buildAll() {
        document.querySelectorAll('.deco-mosaic').forEach(build);
    }

    /* Surfaces inside a closed modal measure 0 x 0 at load, so building once
       on DOMContentLoaded would leave Mission and Updates showing bare grout
       the first time they open. Watching each surface's box covers that, a
       later reflow and a viewport resize with one mechanism — and build()
       is a no-op unless the tile count actually changed. */
    function observe() {
        buildAll();
        if (typeof ResizeObserver !== 'function') return;
        const ro = new ResizeObserver(function (entries) {
            entries.forEach(function (entry) { build(entry.target); });
        });
        document.querySelectorAll('.deco-mosaic').forEach(function (el) { ro.observe(el); });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', observe);
    } else {
        observe();
    }

    // Fallback for browsers without ResizeObserver.
    let resizeTimer = null;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(buildAll, 180);
    });

    window.initDecoMosaic = buildAll;
})();
