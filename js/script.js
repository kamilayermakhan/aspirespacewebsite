        lucide.createIcons();

        /* ============================================================================
           TransferCardController — the one shared A -> B -> C interaction for
           SYSTEM ARCHITECTURE, MISSION and UPDATES.

           The clicked rubricator row becomes a single moving element (backing +
           border + both chamfers + text, all one node) that rises to a common
           rail (vertical only), then travels right to dock as the destination
           heading (horizontal only, width/typography morph via a same-shell
           text crossfade). It remains mounted there — there is no second,
           independent destination heading.

           Geometry is measured from the live DOM (getBoundingClientRect,
           relative to the unified frame) every time, never hardcoded per item
           or per index, so rubricator entries can be added or removed with no
           animation change.
           ============================================================================ */
        function TransferCardController(cfg) {
            this.frame = document.querySelector(cfg.frame);
            this.rail = document.querySelector(cfg.rail);
            this.railLive = cfg.railLive ? document.querySelector(cfg.railLive) : null;
            this.generation = 0;
            this.animations = [];
            this.timers = [];
            this.card = null;
            this.cardSourceText = null;
            this.cardTargetText = null;
            this.sourceLabel = null;
            this.dockedIndex = null;
            this.dockedRow = null;
            this.shell = this.frame ? this.frame.closest('.media-shell') : null;
            if (this.frame) {
                let layer = this.frame.querySelector('.transfer-layer');
                if (!layer) {
                    layer = document.createElement('div');
                    layer.className = 'transfer-layer';
                    this.frame.appendChild(layer);
                }
                this.layer = layer;
                this._ensureBackButton();
            }
        }

        TransferCardController.V_EASE = 'cubic-bezier(.20,.70,.25,1)';
        TransferCardController.H_EASE = 'cubic-bezier(.22,1,.36,1)';
        TransferCardController.H_DURATION = 350;

        TransferCardController.reducedMotion = function () {
            return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        };
        TransferCardController.stackedLayout = function () {
            return window.matchMedia && window.matchMedia('(max-width: 680px)').matches;
        };
        TransferCardController.clamp = function (v, lo, hi) {
            return Math.min(hi, Math.max(lo, v));
        };

        function px(value) {
            const n = parseFloat(value);
            return Number.isFinite(n) ? n : 0;
        }

        /* The rubricator label inside a row — its text is what travels. */
        function sourceLabelFor(row) {
            return row && (row.querySelector('.media-index-item-title, .media-index-item-outlet') || row);
        }

        TransferCardController.prototype._ensureCard = function () {
            if (this.card) return this.card;
            const card = document.createElement('div');
            card.className = 'transfer-card transfer-band-v3';
            card.setAttribute('aria-hidden', 'true');
            const label = document.createElement('span');
            label.className = 'transfer-band-label';
            card.appendChild(label);
            this.layer.appendChild(card);
            this.card = card;
            this.bandLabel = label;
            return card;
        };

        /* ---------- Narrow-viewport drill-down ----------
           Below 680px the index and the article can't sit side by side and
           stay legible, so the explorer becomes a two-level master/detail
           view instead: the full-width faceted index first, then the article
           on its own once a card is picked, with a back control in the
           shell's own header bar (rather than any new chrome inside the
           workspace, which the docked band already occupies). The state
           lives on the shell so the header, the index, the stage and the
           band can all key off one class. */
        TransferCardController.prototype._ensureBackButton = function () {
            const header = this.shell ? this.shell.querySelector('.media-shell-header') : null;
            if (!header || header.querySelector('.shell-back')) return;
            const back = document.createElement('button');
            back.type = 'button';
            back.className = 'shell-back';
            back.textContent = '← INDEX';
            const self = this;
            back.addEventListener('click', function () { self.exitDetail(); });
            header.insertBefore(back, header.firstChild);
        };

        TransferCardController.prototype.enterDetail = function () {
            if (this.shell) this.shell.classList.add('is-detail');
            if (this.frame) this.frame.classList.add('is-detail');
        };

        TransferCardController.prototype.exitDetail = function () {
            if (this.shell) this.shell.classList.remove('is-detail');
            if (this.frame) this.frame.classList.remove('is-detail');
            if (this.dockedRow && typeof this.dockedRow.scrollIntoView === 'function') {
                this.dockedRow.scrollIntoView({ block: 'nearest' });
            }
        };

        TransferCardController.prototype._cancelActive = function () {
            this.generation++;
            this.animations.forEach(function (a) { try { a.cancel(); } catch (err) {} });
            this.animations = [];
            this.timers.forEach(function (t) { clearTimeout(t); });
            this.timers = [];
        };

        TransferCardController.prototype._restorePreviousLabel = function () {
            if (this.sourceLabel) {
                this.sourceLabel.classList.remove('media-index-item--transferring');
                this.sourceLabel = null;
            }
        };

        /* Geometry for one card: where it starts (the clicked row) and where it
           docks. On the wide side-by-side layout the band spans the whole
           frame, at the same top edge the rubricator and the stage already
           share, and relies on the row directly underneath being the blank,
           just-scrolled-to-top one so nothing shows through. On the narrow
           rail layout (stackedLayout()) — used by SYSTEM ARCHITECTURE at
           every width and by MISSION/UPDATES under 680px — the rail is a
           persistent side column rather than something rows scroll past
           underneath the band, so the band is confined to the stage
           column's own bounds instead: it can never overlap the rail, so
           the rail's rows stay fully visible (see transferTo, which skips
           blanking the source row there for the same reason). Measured
           fresh every call — nothing here is hardcoded per item or index. */
        TransferCardController.prototype._measureBand = function (row) {
            if (!this.frame || !row) return null;

            const frameRect = this.frame.getBoundingClientRect();
            const frameCS = getComputedStyle(this.frame);
            const rowRect = row.getBoundingClientRect();
            const labelNode = sourceLabelFor(row);
            const labelRect = labelNode.getBoundingClientRect();
            const topInset = px(frameCS.paddingTop);

            const stage = this.frame.querySelector('.media-stage');
            const stageRect = stage ? stage.getBoundingClientRect() : frameRect;
            const stacked = TransferCardController.stackedLayout();
            const dockX = stacked ? (stageRect.left - frameRect.left) : 0;
            const dockY = stacked ? (stageRect.top - frameRect.top) : topInset;
            const dockWidth = stacked ? stageRect.width : frameRect.width;

            /* Measured relative to the frame first, since that's the common
               coordinate space for both the scroll/body padding lookup and
               the stage rect. The card itself docks at dockX, and the label
               is a child of the card (see _ensureCard) — so what actually
               gets assigned to label.style.left must be relative to the
               card's own left edge, not the frame's, or the two offsets
               stack and push the label past the card's right edge entirely
               once dockX is non-zero (the narrow-rail layout). */
            const scroll = this.frame.querySelector('.media-article-scroll');
            const body = this.frame.querySelector('.media-article-body');
            let labelXInFrame;
            if (scroll) {
                const scrollRect = scroll.getBoundingClientRect();
                const scrollCS = getComputedStyle(scroll);
                const bodyCS = body ? getComputedStyle(body) : null;
                labelXInFrame = scrollRect.left - frameRect.left + px(scrollCS.paddingLeft) + (bodyCS ? px(bodyCS.paddingLeft) : 0);
            } else {
                labelXInFrame = stageRect.left - frameRect.left + 18;
            }

            /* The label's docked width is the room actually available at the
               dock, not the source row's — the row lives in a narrow rail
               (especially on the stacked/narrow layout), so reusing its width
               at the destination wrapped long headlines one word per line. */
            const dockLabelWidth = Math.max(1, (dockX + dockWidth) - labelXInFrame - 16);
            const labelX = labelXInFrame - dockX;

            return {
                start: {
                    x: rowRect.left - frameRect.left,
                    y: rowRect.top - frameRect.top,
                    width: rowRect.width,
                    height: rowRect.height,
                    labelX: labelRect.left - rowRect.left,
                    labelY: labelRect.top - rowRect.top,
                    labelWidth: labelRect.width,
                    labelHeight: labelRect.height
                },
                dock: { x: dockX, y: dockY, width: dockWidth, labelX: labelX, labelWidth: dockLabelWidth }
            };
        };

        TransferCardController.prototype._reserveBandSpace = function (height) {
            if (!this.frame) return;
            this.frame.style.setProperty('--transfer-band-reserve', Math.ceil(height + 10) + 'px');
            this.frame.classList.add('has-transfer-band');
        };

        /* Snap the docked card back onto the band with no animation — used after
           resize, where an in-flight or already-landed card's pixel geometry is
           stale relative to the (possibly reflowed) frame. */
        TransferCardController.prototype.resync = function () {
            if (!this.card || this.dockedIndex === null || !this.dockedRow || !this.frame) return;
            this._cancelActive();
            const m = this._measureBand(this.dockedRow);
            if (!m) return;
            this.card.style.transform = '';
            this.card.style.left = m.dock.x + 'px';
            this.card.style.top = m.dock.y + 'px';
            this.card.style.width = m.dock.width + 'px';
            this.card.style.height = m.start.height + 'px';
            this.bandLabel.style.left = m.dock.labelX + 'px';
            this.bandLabel.style.top = m.start.labelY + 'px';
            this._reserveBandSpace(m.start.height);
        };

        /* Cancel any in-flight transfer, restore the idle state and hide the
           card. Used when a modal/explorer resets to its idle view. */
        TransferCardController.prototype.reset = function () {
            this._cancelActive();
            this._restorePreviousLabel();
            this.dockedIndex = null;
            this.dockedRow = null;
            this.exitDetail();
            if (this.card) this.card.style.display = 'none';
            if (this.frame) {
                this.frame.classList.remove('has-transfer-band');
                this.frame.style.removeProperty('--transfer-band-reserve');
            }
        };

        /*
           row            — the clicked rubricator <button>. Must already be the
                             first visible row of its list (selectCatalogueItem
                             below is responsible for scrolling it there first).
           index          — its stable index (identity only, never used for
                             geometry/timing)
           text           — the rubricator title. It is also the docked heading:
                             the label's typography is copied once from the
                             source row and never changed, so nothing morphs —
                             only its position/width animate.
           prepareContent — synchronous callback: unhides the article pane and
                             populates body content (image/text/etc). Runs before
                             the destination is measured, so a pane that was
                             `hidden` reports real geometry.
           immediate      — skip the animation and dock directly (initial load)
        */
        TransferCardController.prototype.transferTo = function (row, index, text, prepareContent, immediate) {
            if (!this.frame || !row) return;

            this._cancelActive();
            this._restorePreviousLabel();

            const sourceLabelNode = sourceLabelFor(row);
            const sourceCS = getComputedStyle(sourceLabelNode);
            const before = this._measureBand(row);
            if (!before) return;

            const token = this.generation;
            this.sourceLabel = row;
            this.dockedIndex = index;
            this.dockedRow = row;

            if (typeof prepareContent === 'function') prepareContent();
            if (this.railLive) this.railLive.textContent = text;

            /* Only a real pick drills into the detail view; the initial
               auto-selection (immediate) leaves a narrow viewport sitting on
               the index, which is the level a visitor should land on. This
               runs after `before` is measured, so the source row's geometry
               is still the one from the visible index. */
            if (!immediate) this.enterDetail();

            /* Content may have changed the stage geometry (image loaded, article
               body height changed); recompute the destination while keeping the
               exact source-row dimensions and typography captured above. */
            const after = this._measureBand(row) || before;
            const start = before.start;
            const dock = after.dock;

            /* On the stacked mobile layout the band docks above the stage, not
               over the list (see _measureBand) — the row stays fully readable
               there, so blanking its text would just look like it vanished.
               .is-active (toggled by prepareContent) is the selection signal
               on mobile instead. */
            if (!TransferCardController.stackedLayout()) {
                row.classList.add('media-index-item--transferring');
            }

            const card = this._ensureCard();
            const label = this.bandLabel;
            const self = this;

            card.style.display = '';
            card.style.transform = '';
            card.style.left = start.x + 'px';
            card.style.top = start.y + 'px';
            card.style.width = start.width + 'px';
            card.style.height = start.height + 'px';

            label.textContent = text;
            label.style.left = start.labelX + 'px';
            label.style.top = start.labelY + 'px';
            label.style.width = Math.max(start.labelWidth, 1) + 'px';
            label.style.height = Math.max(start.labelHeight, 1) + 'px';
            label.style.opacity = '1';
            label.style.fontFamily = sourceCS.fontFamily;
            label.style.fontWeight = sourceCS.fontWeight;
            label.style.fontSize = sourceCS.fontSize;
            label.style.letterSpacing = sourceCS.letterSpacing;
            label.style.lineHeight = sourceCS.lineHeight;
            label.style.textTransform = sourceCS.textTransform;
            label.style.color = sourceCS.color;
            label.style.textAlign = sourceCS.textAlign;
            label.style.whiteSpace = sourceCS.whiteSpace;
            label.style.textOverflow = sourceCS.textOverflow;

            const finish = function () {
                if (token !== self.generation) return;
                card.style.transform = '';
                card.style.left = dock.x + 'px';
                card.style.top = dock.y + 'px';
                card.style.width = dock.width + 'px';

                /* The label's width at the dock can be much wider (or, on the
                   narrow rail layout, sometimes narrower) than it was on the
                   source row, so its wrapped line count — and therefore the
                   band's height — isn't known until it's actually laid out at
                   that width. Measure it live instead of reusing the source
                   row's height. */
                label.style.left = dock.labelX + 'px';
                label.style.width = Math.max(dock.labelWidth, 1) + 'px';
                label.style.height = 'auto';
                const labelHeight = Math.max(label.scrollHeight, start.labelHeight, 1);
                const cardHeight = Math.max(start.height, labelHeight + start.labelY * 2);

                card.style.height = cardHeight + 'px';
                label.style.top = start.labelY + 'px';
                label.style.height = labelHeight + 'px';
                label.style.opacity = '1';
                self._reserveBandSpace(cardHeight);
                self.animations = [];
                self.timers = [];
            };

            if (immediate || TransferCardController.reducedMotion() || TransferCardController.stackedLayout()) {
                finish();
                return;
            }

            const dy = dock.y - start.y;
            const vDuration = TransferCardController.clamp(Math.abs(dy) * 0.35, 100, 220);

            const vAnim = card.animate(
                [{ transform: 'translate(0px,0px)' }, { transform: 'translate(0px,' + dy + 'px)' }],
                { duration: vDuration, easing: TransferCardController.V_EASE, fill: 'forwards' }
            );
            this.animations = [vAnim];

            // Phase sequencing runs on setTimeout, not Animation#finished: under an
            // interrupted (cancel + immediately re-animate) sequence a just-cancelled
            // Animation's `finished` promise can sit pending well past its nominal
            // duration before the browser settles it, which would stall the very next
            // phase. A timer keyed to the same duration is unaffected and keeps rapid
            // repeated clicks responsive; token/generation guards below still make any
            // stale timer a no-op.
            const phase1Timer = setTimeout(function () {
                if (token !== self.generation) return;
                card.style.top = dock.y + 'px';
                card.style.transform = '';
                try { vAnim.cancel(); } catch (err) {}

                const bandAnim = card.animate(
                    [
                        { left: start.x + 'px', width: start.width + 'px' },
                        { left: '0px', width: dock.width + 'px' }
                    ],
                    { duration: TransferCardController.H_DURATION, easing: TransferCardController.H_EASE, fill: 'forwards' }
                );
                const labelAnim = label.animate(
                    [{ left: start.labelX + 'px' }, { left: dock.labelX + 'px' }],
                    { duration: TransferCardController.H_DURATION, easing: TransferCardController.H_EASE, fill: 'forwards' }
                );
                self.animations = [bandAnim, labelAnim];

                const phase2Timer = setTimeout(function () {
                    if (token !== self.generation) return;
                    try { bandAnim.cancel(); labelAnim.cancel(); } catch (err) {}
                    finish();
                }, TransferCardController.H_DURATION);
                self.timers = [phase2Timer];
            }, vDuration);
            this.timers = [phase1Timer];
        };

        /* ----------------------------------------------------------------------
           selectCatalogueItem — the ONE lifecycle shared by Mission, Updates and
           System Architecture:

             1. cancel whatever this controller is currently doing;
             2. restore the previously-selected row's label immediately (it is
                structurally present the whole time — only its text was hidden);
             3. scroll the catalogue (real scrollTop, item order never changes)
                until the clicked row is the first visible row;
             4. only then transfer that row's title into the band on the right.

           A single controller.generation token guards both phases, so a second
           click while a scroll or transfer is still in flight cancels it
           cleanly — there is never more than one moving band and never more
           than one blank source row.
           ---------------------------------------------------------------------- */
        function easeOutQuart(t) { return 1 - Math.pow(1 - t, 4); }

        function scrollRowToTop(list, row, controller, token) {
            return new Promise(function (resolve) {
                if (!list || !row) { resolve(false); return; }

                const rowRect = row.getBoundingClientRect();
                const listRect = list.getBoundingClientRect();
                const rowHeight = Math.max(1, rowRect.height);

                // Give the catalogue enough trailing space for even the last row
                // to reach the top slot without changing record order.
                const reserve = Math.max(14, list.clientHeight - rowHeight + 14);
                list.style.paddingBottom = reserve + 'px';
                void list.offsetHeight;

                const from = list.scrollTop;
                const unclamped = from + (rowRect.top - listRect.top);
                const maxScroll = Math.max(0, list.scrollHeight - list.clientHeight);
                const target = Math.max(0, Math.min(maxScroll, unclamped));
                const distance = target - from;

                if (TransferCardController.reducedMotion() || Math.abs(distance) < 1) {
                    list.scrollTop = target;
                    resolve(token === controller.generation);
                    return;
                }

                const duration = Math.max(150, Math.min(340, Math.abs(distance) * 0.42));
                const start = performance.now();

                const tick = function (now) {
                    if (token !== controller.generation) { resolve(false); return; }
                    const t = Math.min(1, (now - start) / duration);
                    list.scrollTop = from + distance * easeOutQuart(t);
                    if (t < 1) requestAnimationFrame(tick);
                    else { list.scrollTop = target; resolve(true); }
                };
                requestAnimationFrame(tick);
            });
        }

        function selectCatalogueItem(controller, list, row, index, text, prepareContent, immediate) {
            if (!controller || !row) return;

            controller._cancelActive();
            controller._restorePreviousLabel();
            if (controller.card) controller.card.style.display = 'none';
            if (controller.frame) {
                controller.frame.classList.remove('has-transfer-band');
                controller.frame.style.removeProperty('--transfer-band-reserve');
            }
            controller.dockedIndex = null;
            controller.dockedRow = null;

            const token = controller.generation;
            const proceed = function () {
                if (token !== controller.generation) return;
                controller.transferTo(row, index, text, prepareContent, immediate);
            };

            /* Wide layout: the index and the article share the screen, so the
               picked row scrolls up into the top slot the band then rises out
               of, and the transfer waits for that scroll to land.

               Narrow layout: the pick drills into a detail view that replaces
               the index entirely (see enterDetail), so there is no top slot to
               scroll to and nothing for a wait to protect — it would only open
               a ~150-340ms window with the band and article torn down and
               nothing drawn yet, which read as the heading vanishing. Update
               straight away instead, and just keep the picked row in view for
               when the reader comes back to the index. */
            if (immediate || !list) {
                proceed();
                return;
            }

            if (TransferCardController.stackedLayout()) {
                proceed();
                if (typeof row.scrollIntoView === 'function') row.scrollIntoView({ block: 'nearest' });
                return;
            }

            scrollRowToTop(list, row, controller, token).then(function (ok) {
                if (ok) proceed();
            });
        }

        const architectureTransfer = new TransferCardController({
            frame: '#architectureWorkspace',
            rail: '#oryxTitle',
            railLive: '#oryxTitleLive'
        });
        const missionTransfer = new TransferCardController({
            frame: '#missionWorkspace',
            rail: '#missionTitle',
            railLive: '#missionTitleLive'
        });
        const mediaTransfer = new TransferCardController({
            frame: '#mediaWorkspace',
            rail: '#mediaTitle',
            railLive: '#mediaTitleLive'
        });
        window.addEventListener('resize', function () {
            architectureTransfer.resync();
            missionTransfer.resync();
            mediaTransfer.resync();
        });

        function openModal(id) {
            const modal = document.getElementById(id);
            if (!modal) return;

            modal.classList.remove('hidden');
            document.documentElement.classList.add('modal-open');

            if (id === 'media-modal' && typeof window.resetMediaExplorer === 'function') {
                window.resetMediaExplorer();
                requestAnimationFrame(() => {
                    if (window.mediaSilverWorldMap) window.mediaSilverWorldMap.resize();
                });
            }

            if (id === 'mission-modal' && typeof window.resetMissionExplorer === 'function') {
                window.resetMissionExplorer();
                requestAnimationFrame(() => {
                    if (typeof window.resizeMissionCanvas === 'function') window.resizeMissionCanvas();
                });
            }
        }

        function closeModal(id) {
            const modal = document.getElementById(id);
            if (!modal) return;

            modal.classList.add('hidden');
            document.documentElement.classList.remove('modal-open');
        }

        function tick(){
            const d = new Date(Date.now() + new Date().getTimezoneOffset()*60000 + 4*3600000);
            const p = n => (n<10?'0':'') + n;
            const timeStr = p(d.getHours()) + ':' + p(d.getMinutes()) + ' SYS';
            const el1 = document.getElementById('clock');
            const el2 = document.getElementById('clock-desktop');
            if(el1) el1.textContent = timeStr;
            if(el2) el2.textContent = timeStr;
        }
        tick(); setInterval(tick, 20000);

        const MEDIA_GEOTAGS = [
            "Abu Dhabi, UAE",
            "Baikonur, Kazakhstan · UAE",
            "UAE, Shanghai",
            "Dubai, UAE",
            "Abu Dhabi, UAE",
            "Abu Dhabi, UAE",
            "Abu Dhabi, UAE",
            "Dubai, UAE",
            "Dubai, UAE"
        ];

        const MEDIA_RELEASES = [
            {                outlet: "Fast Company",
                date: "07 JUN 2026",
                title: "AI, ex-Soviet engineers, and the Holy Grail of rocketry: Inside the bold bet to rival SpaceX",
                badge: "Fast Company",
                url: "https://www.fastcompany.com/91563020/aspire-rocket-design-spacex",
                fileId: "1sFuNU6yguRJlzr9MY11GT6lSFO98YG1q",
                imageData: "assets/images/press/1sFuNU6yguRJlzr9MY11GT6lSFO98YG1q.jpg",
                rows: [["OUTLET", "Fast Company"], ["DATE", "07 JUN 2026"]],
                articleHtml: "<article class=\"media-article\"><p class=\"media-article-deck\">The aerospace startup Aspire is designing a fully reusable rocket that could make launches cheaper. It might just beat Elon Musk at his own game.</p><p>“The engine that we have now could have probably taken seven years and up to half a billion dollars,” Stan Rudenko tells me over a video call from Abu Dhabi. “In our collaboration, it basically took half a year . . . and we already have a first version. It’s mind-blowing.”</p><p>Rudenko is the CEO of Aspire Space Technologies, and the collaboration he’s talking about is with Leap 71, a Dubai-based computational engineering startup founded by the aerospace engineer Josefine Lissner and the entrepreneur Lin Kayser. They have formed an almost sci-fi alliance: A team staffed by the legends of the Soviet space program—engineers who built the Energia rocket and the fully autonomous Buran space shuttle—is joining forces with an autonomous AI software system and HBD, a Shanghai-based large-format metal additive manufacturer. Their goal? To build a fully reusable orbital rocket.</p><p>If they pull it off, they could become the most formidable enemy to SpaceX’s quasimonopoly on the commercial space economy. They plan to do it not by copying Elon Musk’s massive Starship, but by resurrecting the decades-old aerospace dream of the aerospike engine, a rocket engine that uses an exhaust cone instead of an exhaust bell, allowing it to work at any altitude. They want to put it on Oryx, a two-stage vehicle that will make space launches cheaper than what’s available today.</p><p>If it all works and they complete their timeline—from its late 2026 full-scale engine test to its 2031 first flight—Oryx will be the first fully reusable rocket. That’s a big if, since nothing in this industry is guaranteed to work.</p><p>To understand why this is a big deal, you have to look at the current launch market. The laws of orbital physics set a limited number of launches per spaceport, and there is a limited number of spaceports around the world. Currently there are 28, almost half controlled by the U.S. and most of the rest controlled by China and Russia, with Japan, Europe, and India controlling one each.</p><p>Right now, there are about 2,400 satellites made annually, without counting SpaceX’s own satellites, and 600 of those can’t be launched. Satellite companies face 18- to 24-month timeframes for launch slots. This is only going to get worse as the space industry grows, according to analysts.</p><p>Plus, the most active private launch companies today, SpaceX and Blue Origin, are hoarding capacity for their own megaconstellations of AI servers and satellites. “Starship will be launching Elon’s data centers and not StarCloud’s,” Rudenko points out, noting that the commercial launch market is becoming dangerously vertically integrated. There’s a big world outside the U.S. and China—Chinese companies are also using their launch capacity for their own satellites—that is starved for launch slots. Because the fully reusable Oryx is designed to fly, land, and turn around rapidly like a commercial airliner, it aims to provide a dedicated, high-frequency flight schedule. Aspire is betting that this speed will be the key to absorb the launch backlog.</p><p>Musk’s answer to everything is Starship, a rocket that is twice as powerful as the Saturn V, stands 394 feet tall, and consumes 1.2 million gallons of fuel in each launch to carry from 220,000 to 300,000 pounds of satellites to orbit. Given that your typical satellite weighs 1,100 to 2,000 pounds, this thing is too big to make sense for many commercial operations. It’s the equivalent of a giant semitruck you have to completely fill with small Amazon packages before it makes economic sense to drive.</p><p>It’ll be great to mass-deploy SpaceX’s fabled massive constellations of AI servers and Starlink satellites. Or to go to the moon and Mars. But integrating anything from 136 to 170 third-party satellites into one Starship launch will be an operational nightmare.</p><p>Aspire is building a launch vehicle called Oryx that competes in terms of payload with SpaceX’s 229.6-foot-tall Falcon 9. The latter hits the sweet spot for commercial payloads: At 38,000 pounds of total cargo, it can comfortably fit a handful of medium-size satellites, plus a variable number of smaller satellites.</p><p>Right now, the Falcon 9’s top stage is disposable and only the main booster stage gets back to Earth. The launch price per kilogram ranges from $2,500 to $3,000, making it the cheapest way to reach orbit. The Oryx, Rudenko promises, will cut down on the launch price by making the entire rocket reusable. The company’s estimates claim the Oryx will get launch prices down to a shocking $200 per kilogram, beating Musk by more than a factor of 10.</p><h4>The Oryx</h4><p>The Oryx is a fully integrated, fully reusable two-stage space transportation system engineered for rapid turnaround flights. Drawing on the heavy-lift DNA of the Soviet Buran-Energia program that its engineers worked on decades ago, the architecture relies on 10 liquid methane and liquid oxygen (methalox) engines. Five large 1,000-kilonewton engines push the first-stage booster off the pad, while five 200-kilonewton engines take over to push the upper stage into orbit.</p><p>Visually, the Oryx truly looks like a modern sci-fi spaceship. It’s unlike anything we have seen in real spaceflight history. Sitting atop its first stage, it’s neither a fragile capsule perched on a disposable stick like the Dragon nor the silver bullet of Starship.</p><p>While its first stage is the functional equivalent of the Falcon 9, the real innovation is what happens at the top. The upper stage isn’t just a cargo container that ferries satellites like the one used by SpaceX’s workhorse. Called the D2 Cargo, it’s an autonomous spaceship that sports landing legs and aerodynamic strakes. It doesn’t look at all like a traditional rocket stage but more like a ship from The Expanse, a sci-fi series set in a future where humanity has colonized the entire solar system.</p><p>In the TV series, spaceships follow a minimalist design philosophy akin to Dieter Rams’ principles of design. Their form follows function, but the result is aesthetically pleasing, elegant shapes that fulfill the requirements for orbital operations and reentry, but at the same time are a dance of smooth surfaces that truly feel like the future. It’s the antithesis of Starship, which has the retrofuturistic polished stainless steel pointy bullet look of old Flash Gordon cartoonish vehicles.</p><p>Aspire aims to fly the Oryx in three ways. One is a traditional fully expendable mode—where the upper stage burns up in the atmosphere or crashes into the sea—carrying 15 metric tons to low earth orbit. Two is landing the booster like a Falcon 9, in which case it can carry 12.5 tons. But three is the ultimate goal—the fully reusable mode. This allows the D2 Cargo to carry 3 tons of payload into orbit, maneuver around, refuel space stations, or act as a standalone floating laboratory for pharma and semiconductor research, and then safely fly its 3-ton cargo back down to Earth to be used again.</p><p>Making a Falcon 9-sized upper stage fully reusable is a difficult physics problem. You have to carry engines that work in the vacuum of space, plus engines that work at sea level to land the ship. Starship solves this by just being gargantuan—it carries two sets of engines, absorbing the massive weight penalty. A smaller ship can’t afford that dead weight.</p><p>The elegant solution is the aerospike. “The aerospike has the same efficiency when it is in space, but it also allows it to land on Earth,” Kayser explains. The ship comes down, stops on the power of its own exhaust, hovers for a second, and gently lands. The aerospike is lighter and significantly more efficient than a vacuum engine. This efficiency comes from its shape.</p><p>(1/10th scale test engine)</p><p>Unlike the conventional bell-shaped nozzles we are all familiar with, an aerospike acts like an inside-out engine. It channels supersonic exhaust along a central cone that starts wide and ends in a point, much like a slightly concave ice cream cone. This shape allows the expanding gases to adjust naturally to atmospheric pressure.</p><p>That’s why aerospikes have been the Holy Grail of space flight for decades. NASA spent years and millions of dollars trying to make aerospikes work in the 1990s with the X-33 program. They failed. The problem was that the spike sits in the middle of exhaust gas heated to 5,430 degrees Fahrenheit (almost 3,000 Celsius) that aggressively melts the metal.</p><p>This is where AI came to the rescue. Rather than human engineers trying to manually draw impossibly intricate internal cooling channels in CAD software, Leap 71 uses an in-house AI model called Noyron. Noyron is essentially a real-world Jarvis—Tony Stark’s AI assistant-engineer from the Iron Man movies. The computational AI model is encoded with thermodynamics, fluid dynamics, and manufacturing constraints discovered in decades of rocketry research by the United States and the Soviet Union.</p><p>Just a few months ago, Leap 71 partnered with the Shanghai-based manufacturer HBD to 3D-print the XRA-2E5, a monolithic methalox aerospike capable of generating 20 tons of thrust, like the Blue Origin BE-3U in the upper stage of Jeff Bezos’s New Glenn rocket. Noyron autonomously designed the intricate regenerative cooling system of the aerospike: Inside the smooth walls of the engine there is a 3D-printed network of channels that carry the cryogenic liquid oxygen and methane from the rocket’s fuel tanks to the combustion chamber. Since these liquids have a very low temperature (minus 297 degrees Fahrenheit for the oxygen and minus 260 for the methane), the fuel channels act as the cooling element for the spike and the combustion chamber.</p><p>HBD used a massive 10-laser printer to build the one-meter-tall (39-inch) engine out of a superalloy called Inconel 718 in just 289 hours. It’s the largest 3D-printed aerospike ever made, and it proves Noyron can scale to orbital-class thrust.</p><p>(1/10th scale test engine)</p><h4>Time to fire up</h4><p>But having a beautiful perfect piece of printed metal sitting on a trade show floor is very different from surviving 20 tons of controlled explosions. While Leap 71 already successfully tested aerospikes created by Noyron back in 2025, Kayser tells me that the bigger XRA-2E5 was a manufacturing test to prove the 3D-printing process wouldn’t fail structurally. The actual hot-fire test engine is what they are working toward next.</p><p>Their biggest problem isn’t the AI, the physics, or the printers but finding the right testing site. “We can design these things now much quicker than we actually can build the infrastructure to test it,” Kayser admits. Finding a test stand and propellant farm capable of handling a 200-kilonewton methalox engine is a massive undertaking. The testing facility is their primary bottleneck.</p><p>To solve this, they need to either build massive new test infrastructure from scratch or borrow someone else’s. Kayser says the United Arab Emirates government is highly interested in supporting the construction of a dedicated test site in the desert. But building a heavy-duty propellant farm takes serious time. That’s why Leap 71 is looking at Baikonur in Kazakhstan—which still houses heavy Soviet-era aerospace infrastructure—to see if they can use its facilities just to get the engine hot-fired this year.</p><p>But while the engine test-stand situation is still being negotiated, the launchpad for Aspire’s Oryx rocket is locked down. Aspire already has a launchpad in Baikonur. Operating from the historic cosmodrome where the Soviets built their space empire is important. First, Baikonur is in Rudenko’s (and his team’s) blood. His father actually managed the spaceport. Now, a new generation of ex-Soviet engineers is returning to the Kazakh steppes to test a decidedly 21st-century spacecraft.</p><p>Baikonur also provides a huge operational advantage over SpaceX. Musk’s rockets launch from the U.S. coast. To save fuel, SpaceX prefers to land the Falcon 9 booster out in the ocean on an autonomous drone ship, which is a logistical headache. If they want to fly the booster back to land, it requires a heavy fuel penalty to turn the rocket around in midflight.</p><p>Aspire’s architecture avoids this by using the vast, empty geography of the steppes and the legacy logistics of the Soviet rail system. When the Oryx launches, the D2 Cargo upper stage will deploy its payload in orbit and eventually fly all the way back to the launchpad. But the first-stage booster won’t waste fuel turning around.</p><p>“What we can do in Kazakhstan is you can fly downrange, land in the desert, and take the train back to the actual launch site,” Rudenko explains. You simply drop the booster in an empty stretch of desert, load it onto a railcar, and roll it home. “You don’t have to deal with the operations and shifts and waves and salt water spraying. All of these things are really not great for rockets.”</p><h4>Final countdown</h4><p>“Our next big, big milestone is in 2028,” Rudenko tells me. “We’re going to make a hopper test of our second-stage spaceship.” The company plans to launch the 16-meter-tall D2 Cargo ship from Baikonur, push it to an altitude of about 0.6 miles on the power of Leap 71’s aerospike engine, hover in midair, and bring it gently back down to the pad. It’s the same kind of low-altitude proving flight SpaceX used to validate the Starship architecture, proving out the software, the propulsion stack, and the landing systems all at once.</p><p>If the hopper test works, it paves the way for full orbital test flights targeted for 2031. It’s a very ambitious timeline but Rudenko and Kayser are 100% sure it will be done. In fact, the former claims they are ahead of schedule with every milestone so far.</p><p>And yet, the aerospike hasn’t breathed fire yet, and orbital spaceflight is notoriously unforgiving, as Soviet engineers know. But with Aspire’s internal estimates suggesting this fully reusable system could drop payload costs to an absurd $200 per kilogram, there is motivation for sure. If this unlikely alliance of ex-Soviet rocketeers and AI software engineers can survive the test stand, we might see the rise of a new space power: an agile, high-cadence space fleet that can rival Musk and Bezos the same way the Soviet Union once challenged the United States. This time, with the almighty Chinese also in, it will be a much tighter race. It may have no winners this time because, no matter who gets ahead initially, the launch market and the future space economy, the ultimate technological revolution, will be big enough for everyone.</p><h4>ABOUT THE AUTHOR</h4><p>Jesus Diaz is a screenwriter and producer whose latest work includes the mini-documentary series Control Z: The Future to Undo, the futurist daily Novaceno, and the book The Secrets of Lego House. More</p></article>"
            },
            {                outlet: "24KZ",
                date: "11 MAY 2026",
                title: "Kazakhstan-UAE: cooperation in the space sector",
                badge: "24KZ",
                url: "https://24.kz/kz/zha-aly-tar/kogam/767772-kazakstan-baa-garys-salasyndagy-yntymaktastyk",
                imageData: "assets/images/press/1778403980_42c271eacca4a6d59409.avif",
                rows: [["OUTLET", "24KZ"], ["DATE", "11 MAY 2026"]],
                articleHtml: "<article class=\"media-article\"><p class=\"media-article-deck\">A new Emirati missile system may be launched from Baikonur in the next few years.</p><p>Its feature is that it will be possible to travel to the same celestial body twice and return with cargo. Currently, relevant negotiations are underway with the Kazakh side. This was announced at the exhibition dedicated to the space industry in the United Arab Emirates.</p><p>Projects that combine space technology and artificial intelligence have entered a new phase. Global companies are investing heavily in this endeavor. According to experts, spaceships have become more mobile. A unique engine has been developed, and a rocket system has been invented that can carry cargo in the opposite direction.</p><p>Stan Rudenko, head of the spacecraft project: – I can say that the project we have developed has no analogues. It is designed for multiple use of the rocket. It can fly into space and return to Earth. Our company is located in the Emirates. We are considering taking advantage of the market opportunities, discussing the project with potential partners and testing it. When the time comes, we have a plan to launch from Baikonur.</p><p>Kazakhstan has become a part of this large-scale process. Because Baikonur is known to the world as an important testing ground. A few years ago, the United Arab Emirates launched its first astronaut from our launch pad. Now, the satellite-building institutions of this country intend to continue their cooperation.</p><p>Rauan Mynbay, correspondent: – The United Arab Emirates has joined the ranks of countries that have soared into the sky and firmly entered space. Now, many private satellites for remote monitoring of the Earth are being built here. One of them is even ready for launch. It should be launched into orbit by the end of the year.</p><p>The peculiarity is that the new devices can process information independently using artificial intelligence. Thus, they provide an immediate signal. In the future, the Emirates will use advanced technology to remotely monitor defense facilities and ship movements at sea.</p><p>Hamdullah Mohib, Head of Satellite Manufacturing Company: – We are taking our potential in artificial intelligence and space to a new level. We are even developing and delivering satellite systems to Europe. Our device processes data in orbit, quickly identifies important events, and delivers them promptly. It is useful for civil defense and security. In today’s changing world, a system of this level is very important.</p><p>In general, the emirate has been paying special attention to the development of space in recent years. We are eager to conquer Mars and reach the Moon. Since 2019, two astronauts have flown into space. Two more are in line. Author: Rauan Mynbay</p></article>"
            },
            {                outlet: "Aspire Space × LEAP 71",
                date: "14 MAR 2026",
                title: "LEAP 71's 200 kN Aerospike Engine to Power Aspire Space's Oryx Spacecraft",
                badge: "Aspire Space × LEAP 71",
                url: "https://www.aspire.space/engine",
                fileId: "1UKxW4GVnkb8rR8aO2Ha6XndC0Dcu4Np8",
                imageData: "assets/images/press/1UKxW4GVnkb8rR8aO2Ha6XndC0Dcu4Np8.jpg",
                rows: [["OUTLET", "Aspire Space × LEAP 71"], ["DATE", "14 MAR 2026"]],
                articleHtml: "<article class=\"media-article\"><p class=\"media-article-deck\">The XRA-2E5, the world’s largest 3D-printed aerospike engine, marks the first major propulsion hardware milestone for Aspire’s fully reusable launch system. Hot-fire testing scheduled for later this year.</p><p>— LEAP 71 and Aspire Space today announced that the XRA-2E5 — a 200 kN aerospike rocket engine designed to power the upper stage of Aspire’s fully reusable Oryx spacecraft — has been successfully manufactured. Produced by HBD (Shanghai Hanbang United 3D Tech Co., Ltd.) using large-format metal additive manufacturing, the one-metre-tall cryogenic methalox engine is the world’s largest 3D-printed aerospike to date.</p><p>The XRA-2E5 was engineered using Noyron, LEAP 71’s Large Computational Engineering Model, which generates fully manufacturing-ready designs from first-principles physics and engineering logic without manual design steps.</p><p>HBD printed the engine as a monolithic Inconel 718 structure in 289 continuous hours on the HBD 800, a ten-laser powder-bed fusion system with one of the largest build volumes in commercial metal additive manufacturing. The engine was produced on the first build.</p><p>Aerospike engines differ from conventional bell-nozzle designs in a fundamental respect: rather than being optimised for a single altitude, they maintain high efficiency from sea level to vacuum. The exhaust plume expands along a central spike and self-adjusts as external pressure changes.</p><p>This makes aerospikes particularly well-suited to the upper stage of a fully reusable launch vehicle, which must perform efficiently through the upper atmosphere and into orbit before returning to the launch site.</p><p>The XRA-2E5 uses a regenerative cooling architecture — the outer chamber is cooled by cryogenic methane, and the central spike by liquid oxygen — to manage the intense thermal loads of the combustion environment.</p><p>The engine shares its design lineage with two earlier Noyron-generated aerospike engines that LEAP 71 has hot-fired over the past 15 months. Those prior test campaigns validated the core design approach at smaller thrust classes; the XRA-2E5 scales that validated architecture to the thrust level required for Aspire’s second stage.</p><h4>“</h4><p>Aerospikes are often considered the holy grail of space propulsion. They promise major performance advantages over conventional engines, but their complex geometry has historically made them extremely difficult to design, manufacture and operate. We believe that by combining computational engineering with advanced additive manufacturing, we can finally make them fly. The XRA-2E5 is the hardware proof of that thesis, and Aspire Space’s mission is the destination for it.</p><h4>Josefine Lissner</h4><h4>CEO and Co-Founder of LEAP 71</h4><h4>“</h4><p>The XRA-2E5 is a significant milestone for Aspire and for our propulsion roadmap. We set out to develop a second-stage engine that matches the technical ambition of a fully reusable launch system, and that is what LEAP 71 and HBD have produced. The combination of an aerospike nozzle, computational design, and additive manufacturing is exactly the kind of step-change approach that our programme requires. We are looking forward to seeing it perform on the test stand.</p><h4>Stan Rudenko</h4><h4>CEO of Aspire Space</h4><h4>What Comes Next</h4><p>The XRA-2E5 is currently being exhibited at TCT Asia in Shanghai (Hall 7.1, Booth 7E35) before proceeding to acceptance checks and integration into a dedicated test stand. A full hot-fire test campaign is scheduled for later in 2026 to validate engine performance across its full operating envelope, with results informing the engine configuration for the Oryx second stage and Aspire’s broader propulsion roadmap.</p><p>The XRA-2E5 is the first engine produced under the multi-year propulsion development agreement between Aspire Space and LEAP 71, announced in November 2025. Under that agreement, LEAP 71 is developing a full spectrum of propulsion systems for the Oryx vehicle, spanning both stages of the fully reusable launch system.</p><h4>About Aspire Space</h4><p>Aspire Space is a UAE-headquartered space transportation company developing the Oryx, a fully reusable launch vehicle and spacecraft. The company’s mission is to provide reliable, high cadence access to orbit for commercial, institutional, and sovereign customers.</p><p>Aspire Space is building toward an inaugural launch and is focused on developing a reusable launch architecture that substantially reduces the cost of reaching orbit.</p><h4>Contact Rocketship@aspire.space — www.aspire.space</h4><h4>About LEAP 71</h4><p>LEAP 71 was founded on the vision that radically accelerating real-world engineering is essential to shaping the future of humankind. Strategically based in Dubai, UAE, the company works with customers worldwide to design advanced machinery across aerospace, electric mobility, robotics, and thermal systems.</p><p>A pioneer in the emerging field of Computational Engineering, LEAP 71 designs physical objects autonomously — without manual modeling or human input. At its core is Noyron, a Large Computational Engineering Model that encodes logic, physics, production methodologies, and real-world feedback into a coherent, deterministic system. It has been called “the first AI that builds machines.”</p><p>Noyron generates functional designs in seconds or minutes, optimized for modern manufacturing technologies such as industrial 3D printing.</p><p>A key focus for the company is extending humanity’s footprint in space. LEAP 71 is developing a spectrum of reference designs for space propulsion systems that serve as the DNA for customer-specific engines. Frequent physical testing and validation continuously enrich Noyron’s models.</p><p>LEAP 71 was founded in 2023 by aerospace engineer Josefine Lissner and serial entrepreneur Lin Kayser.</p><h4>Visit the LEAP 71 website for more information.</h4></article>"
            },
            {                outlet: "Aspire Space × LEAP 71",
                date: "19 NOV 2025",
                title: "LEAP 71 and Aspire Space sign landmark agreement to develop rocket engines for the fully reusable Oryx spacecraft",
                badge: "Aspire Space × LEAP 71",
                url: "https://leap71.com/2025/11/19/leap-71-and-aspire-space-sign-landmark-agreement-to-develop-rocket-engines-for-the-fully-reusable-oryx-spacecraft/",
                fileId: "1NMb4R8Ft3mu3DYrVOTrrwMp3XkL8cOG8",
                imageData: "assets/images/press/1NMb4R8Ft3mu3DYrVOTrrwMp3XkL8cOG8.jpg",
                rows: [["OUTLET", "Aspire Space × LEAP 71"], ["DATE", "19 NOV 2025"]],
                articleHtml: "<article class=\"media-article\"><p>Aspire Space, a UAE-based space launch company, and LEAP 71, a Dubai-based pioneer in computational engineering for space propulsion, have signed a formal agreement to collaborate on the development of the Oryx reusable rocketship. The signing ceremony took place at Dubai Airshow, in the presence of HE Minister Dr. Ahmad Belhoul Al Falasi, Chairman of the UAE Space Agency.</p><p>Oryx is a fully reusable, orbital-class launch vehicle designed to deliver up to 15 tons of cargo to low Earth orbit (3 tons in fully reusable mode). Both its booster and upper stage are engineered for rapid reusability — returning to Earth after each mission for quick turnaround and relaunch.</p><p>Building on their ongoing cooperation, Aspire Space is now contracting LEAP 71 to develop the rocket engines powering the Oryx’s second stage. Each engine will produce 20 tons (200 kN) of thrust, and the partners are pursuing two parallel propulsion paths: a conventional engine and a novel aerospike configuration.</p><p>The aerospike concept, long studied but never flown, offers superior efficiency across both atmospheric and vacuum flight regimes — making it particularly well suited for reusable launch systems. LEAP 71 gained international recognition in December 2024 for successfully testing a 5 kN aerospike engine, validating key aspects of its design.</p><p>Both Aspire Space and LEAP 71 are proud members in the UAE Space Agency’s Space Economic Zones Program, an integrated program designed to foster innovation, investment, and commercial growth across the space sector. Through this program, the two companies are contributing to the UAE’s vision of building a globally competitive and sustainable space economy.</p><p>This collaboration marks a major step toward establishing a sovereign UAE orbital launch capability, powered by advanced propulsion technologies developed domestically.</p><h4>About Aspire Space</h4><p>Aspire Space is developing Oryx — a next-generation, fully reusable rocketship. The two-stage architecture pairs a reusable booster with a reusable upper-stage spacecraft, creating a unified system designed for rapid turnaround and high-cadence operations.</p><p>Heritage and development. Oryx is the result of a focused two-year development effort, marking a technical milestone that builds on decades of aerospace heritage, drawing on engineering principles proven in Zenit and Energia–Buran, and refined through programs such as Sea Launch and Argo.</p><p>Main specs:</p><p>Payload capacity: 3t to LEO in fully reusable configuration, (12.5t reusable, 15t expendable)</p><p>Propulsion: 10 MethaLOX engines (5 × 1000 kN first stage; 5 × 200 kN orbital stage)</p><p>Return capability: up to 3 tons cargo from orbit to Earth</p><p>Mission Profiles:</p><p>Space station resupply and servicing</p><p>Cargo and experiment return</p><p>Autonomous orbital laboratory missions</p><p>Future crewed and lunar flights</p><p>Aspire Space was founded by a team of rocket scientists who led prominent projects such as Zenit, Soyuz and Sea Launch, with the aim to advance the humanity to the New Space Age by providing cutting-edge launch and space transportation services</p><p>Co-founder and CTO – Sergey Sopov, renowned launch systems expert</p><p>Co-founder and CEO – Stan Rudenko, serial entrepreneur</p><p>Contact Rocketship@aspire.space — www.aspire.space</p><p>https://www.linkedin.com/company/aspirespaceuae/</p><h4>About LEAP 71</h4><p>LEAP 71 was founded on the vision that radically accelerating real-world engineering is essential to shaping the future of humankind. Strategically based in Dubai, UAE, the company works with customers worldwide to design advanced machinery across aerospace, electric mobility, robotics, and thermal systems.</p><p>A pioneer in the emerging field of Computational Engineering, LEAP 71 designs physical objects autonomously — without manual modeling or human input. At its core is Noyron, a Large Computational Engineering Model that encodes logic, physics, production methodologies, and real-world feedback into a coherent, deterministic system. It has been called “the first AI that builds machines.”</p><p>Noyron generates functional designs in seconds or minutes, optimized for modern manufacturing technologies such as industrial 3D printing.</p><p>A key focus for the company is extending humanity’s footprint in space. LEAP 71 is developing a spectrum of reference designs for space propulsion systems that serve as the DNA for customer-specific engines. Frequent physical testing and validation continuously enrich Noyron’s models.</p><p>LEAP 71 was founded in 2023 by aerospace engineer Josefine Lissner and serial entrepreneur Lin Kayser.</p><p>Visit the LEAP 71 website for more information.</p></article>"
            },
            {                outlet: "The National",
                date: "16 NOV 2025",
                title: "Abu Dhabi businessman raised in Soviet space town on mission to launch rockets in UAE",
                badge: "The National",
                url: "https://www.thenationalnews.com/future/space/2025/11/16/abu-dhabi-businessman-raised-in-soviet-space-town-on-mission-to-launch-rockets-in-uae/",
                fileId: "1mm2MYHfic83I1m1yibu7JFfKzRyFyjoJ",
                imageData: "assets/images/press/1mm2MYHfic83I1m1yibu7JFfKzRyFyjoJ.jpg",
                rows: [["OUTLET", "The National"], ["DATE", "16 NOV 2025"]],
                articleHtml: "<article class=\"media-article\"><p class=\"media-article-deck\">Stan Rudenko wants to build fully reusable launch system</p><p>As a boy growing up on the fringes of the world’s largest spaceport, Stan Rudenko would walk past a full-scale Soyuz launcher on his way to school.</p><p>His town, built exclusively for the Soviet Union’s space programme, revolved around rockets, engineers and astronauts, with monuments to space pioneers on nearly every street corner.</p><p>Mr Rudenko, now 42 and chief executive of Aspire Space in Abu Dhabi, still recalls the roar of rockets being launched from Baikonur Cosmodrome in Kazakhstan, where his father once helped lead operations for the Zenit space programmes.</p><p>“Our whole life was centred around launches and there were plenty of them,” he told The National. “I clearly remember the Buran orbital spaceplane landing flanked by fighter jets. It was a moment of absolute triumph for the whole nation.”</p><p>Stan Rudenko, left, chief executive of Abu Dhabi&#x27;s Aspire Space and Sergey Alekseevich Sopov, a space engineer who worked on the former Soviet Union&#x27;s and Russia&#x27;s biggest space projects. Victor Besa / The National</p><p>Baikonur was the beating heart of the Soviet space empire, a huge, closed-off complex where the world’s first satellite and the first human were blasted off into space.</p><p>After the Soviet Union&#x27;s collapse in 1992 and Kazakhstan gained independence, the programme was severely scaled back. Mr Rudenko’s family, like many others, eventually left the once-thriving rocket town.</p><p>Despite a lifelong fascination with spaceflight, he initially pursued a different career, graduating from a top law school in St Petersburg and working for multinational firms.</p><p>“Life returned me to rockets and now we have some of the best engineers working with us,” he said, proud that he now leads one of the UAE’s most ambitious private-sector projects to build a new generation of fully reusable rockets.</p><h4>Made in the Emirates</h4><p>Aspire Space, originally founded in Luxembourg, has relocated its headquarters to the UAE and plans to manufacture rockets entirely in the country.</p><p>The company is developing Oryx, a two-stage, fully reusable orbital transportation system designed for satellite deployment, space station resupply, in-orbit laboratory missions and cargo return missions.</p><p>Unlike conventional reusable rockets where only the booster is recovered, Mr Rudenko said Oryx is designed so both stages return to Earth.</p><p>“It’s a fully reusable rocket ship. The second stage is a fully fledged spaceship capable of performing diverse orbital missions before returning to Earth. Launch is just the beginning,” he said.</p><p>Mr Rudenko believes true reusability will create a “virtuous cycle” where costs fall as flight frequency increases, similar to aircraft operations.</p><p>“It’s neither economical nor sustainable to drown expensive hardware in the ocean … let’s make it work for us instead,” he said.</p><p>The rocket will be powered by methalox engines being developed in partnership with Dubai’s Leap 71, which designs and builds artificial-intelligence-powered propulsion systems.</p><p>Aspire’s engineering team includes veterans from Zenit, Energia–Buran and Sea Launch, programmes that built the Soviet Union’s most advanced heavy-lift capabilities.</p><p>Sergey Alekseevich Sopov, the company’s chief technology officer, said the design of Oryx draws heavily on this legacy. “Reusability is not only about landing a rocket, it’s about returning its value to the economy,” he said.</p><p>He said it would require an engineering culture built around rapid turnaround, not just recovery.</p><p>“Every structural node, propulsion element and avionics block is designed with a clear understanding of its service life and digital traceability. In a reusable system, there are no small parts,” he said.</p><h4>Launch plans in UAE and Kazakhstan</h4><p>Aspire hopes to operate two launch sites, one in the UAE for sovereign access to space and a second in Kazakhstan for high-cadence commercial missions.</p><p>Mr Rudenko said the UAE site is still under discussion, so Kazakhstan’s established flight corridors make it more suitable for frequent launches.</p><p>He said Oman’s emerging Etlaq spaceport remains an option the company is “watching very closely”. The firm aims to establish a complete manufacturing and testing cycle in the UAE, beginning with engine and full-stage test stands.</p><p>“We have an ambitious timeline for fire-testing of actual hardware. Having these facilities operational is essential,&quot; said Mr Rudenko.</p><p>His company will be presenting their rocket project at the UAE Space Pavilion at Dubai Airshow next week.</p></article>"
            },
            {                outlet: "Aspire Space",
                date: "11 NOV 2025",
                title: "Aspire Space Unveils Oryx, a Fully Reusable Orbital Transportation System",
                badge: "Aspire Space",
                url: "https://www.aspire.space/rocketship",
                fileId: "1b8SxdaRVHFIohkfaRqJ_DTZx4-4HA0Cx",
                imageData: "assets/images/press/1b8SxdaRVHFIohkfaRqJ_DTZx4-4HA0Cx.jpg",
                rows: [["OUTLET", "Aspire Space"], ["DATE", "11 NOV 2025"]],
                articleHtml: "<article class=\"media-article\"><p class=\"media-article-deck\">Next-generation rocketship for high-cadence LEO missions</p><p>Aspire Space today introduced Oryx, a next-generation, fully reusable space transportation system. The two-stage architecture pairs a reusable booster with a reusable upper-stage spacecraft, creating a unified system designed for rapid turnaround and high-cadence operations.</p><p>Heritage and development. Oryx is the result of a focused two-year development effort, marking a technical milestone that builds on decades of aerospace heritage, drawing on engineering principles proven in Zenit and Energia–Buran, and refined through programs such as Sea Launch and Argo.</p><p>Mission profile and performance. Optimized for low Earth orbit (LEO) missions, Oryx rocketship can deliver up to 3 t in a fully reusable configuration (12.5 t with first stage reuse, 15 t expandable). The architecture is designed for future adaptation to crewed and lunar missions.</p><p>Propulsion. The vehicle employs ten methalox (liquid methane/liquid oxygen) engines: five main engines rated at 1,000 kN each and five upper-stage engines at 200 kN each. The engines are being developed in partnership with Dubai-based LEAP 71, a pioneer in computational engineering for propulsion systems.</p><p>Orbital segment. The upper stage, D2 Cargo, operates as an autonomous orbital spacecraft. It can deliver up to 3 t to orbit, supports in-orbit refueling, enables maneuvering of orbital platforms, and can return up to 3 t safely to Earth. D2 Cargo can also serve as a standalone orbital laboratory hub, unlocking new opportunities for high-value industries such as pharma, biotechnology, semiconductors.</p><p>Program milestones. The upper-stage engine hot-fire test is targeted for Q3 2026. The first integrated flight is planned for 2030.</p><h4>Leadership statements.</h4><p>“Since my work on the Energia–Buran program, I’ve believed that the future of spaceflight lies in fully reusable transportation systems. Now, we’re ready to bring that vision to life,” said Sergey Sopov, Chief Technology Officer at Aspire Space.</p><p>“Rapidly reusable and highly versatile systems will become the backbone of a new space economy. With Oryx, we are going to redefine industry standards,” said Stan Rudenko, CEO and Founder of Aspire Space.</p><p>Manufacturing and launch sites. Aspire Space’s manufacturing and operations base is located in the United Arab Emirates. Launch operations are planned in the UAE and Kazakhstan.</p><h4>About Aspire Space</h4><p>Aspire Space is developing fully reusable launch and orbital transportation systems to enable high-cadence, cost-efficient access to low Earth orbit and beyond.</p><p>Founded by a team of space pioneers who led the prominent projects such as Zenit, Soyuz and Sea Launch, Aspire Space aims to advance humanity to the New Space Age by providing cutting-edge launch and space transportation services.</p><h4>Contact Rocketship@aspire.space — www.aspire.space</h4></article>"
            },
            {                outlet: "The National",
                date: "26 JUN 2025",
                title: "Plan for UAE-built rockets primed to boost standing in global space race",
                badge: "The National",
                url: "https://www.thenationalnews.com/future/space/2025/06/26/plan-for-uae-built-rockets-primed-to-boost-standing-in-global-space-race/",
                fileId: "1e0LnyMuyNmSlvLurYDYJ1OjDKrq1dLV_",
                imageData: "assets/images/press/1e0LnyMuyNmSlvLurYDYJ1OjDKrq1dLV_.jpg",
                rows: [["OUTLET", "The National"], ["DATE", "26 JUN 2025"]],
                articleHtml: "<article class=\"media-article\"><p class=\"media-article-deck\">Two companies have teamed up to help the country gain sovereign launch capability</p><p>A major private sector partnership aimed at developing UAE-built reusable rockets is set to propel the country&#x27;s soaring ambitions in the global space race.</p><p>Aspire Space, a European aerospace firm, is relocating its headquarters to the Emirates and has joined forces with Dubai-based Leap 71 to build the two-stage rocket system.</p><p>The vehicle is designed to carry up to 15 tonnes to low-Earth orbit and is scheduled for its debut launch in 2030.</p><p>The agreement could help the UAE establish sovereign access to space, a capability that only a few nations, such as the US, Russia, Europe and China, currently has.</p><p>“We are planning the first launch in 2030, and I would say that it&#x27;s a very ambitious timeline. The very important thing for us, of course, is to have the partnership with the propulsion systems experts,” Stan Rudenko, chief executive of Aspire, told The National.</p><p>Aspire’s rocket will be powered by Methalox engines, using liquid methane and liquid oxygen, designed and developed by Leap 71 using artificial intelligence. The propulsion systems will be built entirely in the UAE.</p><p>A launch site for these rockets has not yet been confirmed, but Lin Kayser, co-founder of Leap 71, said Oman was a promising option.</p><h4>Region&#x27;s growing space sector</h4><p>Oman is developing the Etlaq spaceport – a 10-hour drive from Dubai – and has been carrying out test launches from the site, with commercial operations set for later this decade.</p><p>“Oman has a fantastic place for launching rockets,” said Mr Kayser.</p><p>“So, we’re saying let’s build the rockets and engines here … and then maybe the right place to launch is over there.”</p><h4>Sovereign access to space</h4><p>The UAE has made significant progress in its space ambitions, from sending astronauts to the International Space Station to launching a probe to Mars and developing lunar rovers.</p><p>But one key capability still missing is the ability to launch its own missions using domestically built rockets.</p><p>“Any region that wants to participate in the space economy fundamentally needs sovereign access to space, because otherwise you&#x27;re always relying on someone else,” said Mr Kayser.</p><p>“The other person that you&#x27;re relying on will set the prices and can give you access or not.”</p><p>He pointed to the difficulties faced by global tech giants when relying on foreign launch providers, including how Amazon’s Jeff Bezos was unable to launch his Kuiper satellites because of limited rocket availability.</p><p>“And I think Elon Musk doesn&#x27;t really want to fly this stuff, so it&#x27;s tough for him to launch a competing constellation,” said Mr Kayser.</p><h4>Rockets and engines built in the Emirates</h4><p>Leap 71 is now designing and building the propulsion systems for Aspire’s new reusable rocket, based on its XRB-2E6 engine that produces 2,000 kilonewtons of thrust.</p><p>The work is being done using Noyron, an artificial intelligence model involving an algorithm that can generate rocket engines, including software codes that command the engine how much thrust and propellant it needs to have. It then powers the engine without any human intervention.</p><p>“Our proposition, as Leap 71, is if we build propulsion systems, then launcher companies will come here,” Mr Kayser said.</p><p>“Because you cannot buy propulsion systems on the free market … outside the United States you cannot really do that.</p><p>“Boeing and Airbus builds airframes, but GE and Rolls-Royce build the engines.</p><p>“And that’s basically what we’re proposing for rocketry … it makes the same amount of sense it does for airplanes.”</p><p>Leap 71 has already validated its technology using smaller engines and is now shifting to much larger propulsion systems required for orbital rockets.</p><p>But developing and testing large rocket engines requires specialised centres.</p><p>Omani spaceport offers fan zone to watch rocket launches</p><p>Transporting them across borders is impractical and often restricted due to export controls.</p><p>“You can test them somewhere else, but if you want to build larger engines, you have to build test sites here in the UAE,” Mr Kayser said.</p><p>“You have to produce them here … it’s not like you can just ship them around the world.”</p><p>He said this approach ensures the entire rocket development pipeline, from design to testing and manufacturing, remains in the UAE.</p><h4>From legacy to next generation</h4><p>Aspire was founded in 2023 in Luxembourg by engineers who have spent decades developing major launch systems.</p><p>Many of them worked on the Soviet-era Zenit and Soyuz programmes, as well as the multinational Sea Launch initiative.</p><p>That team is now expanding, with Aspire planning to hire 20 new employees, including rocket scientists, in the UAE.</p><p>The company also has plans to develop a reusable capsule that would send cargo, and eventually humans, to space stations.</p></article>"
            },
            {                outlet: "Aspire Space × LEAP 71",
                date: "26 JUN 2025",
                title: "Aspire Space and LEAP 71 partner to build large reusable space launch systems in the UAE",
                badge: "Aspire Space × LEAP 71",
                url: "https://leap71.com/2025/06/26/aspire-space-x-leap-71-partnership/",
                fileId: "1KfXBKCjCJaIL8CQzplJcrHfzVeuuXj6j",
                imageData: "assets/images/press/1KfXBKCjCJaIL8CQzplJcrHfzVeuuXj6j.jpg",
                rows: [["OUTLET", "Aspire Space × LEAP 71"], ["DATE", "26 JUN 2025"]],
                articleHtml: "<article class=\"media-article\"><p>Aspire Space and LEAP 71 today announced a strategic partnership to develop a new large reusable launch vehicle capable of delivering up to 15 metric tons to low Earth orbit (LEO).</p><p>Founded in Luxembourg, Aspire Space is led by veterans of major launch programs, including Zenit, Soyuz, and Sea Launch. LEAP 71, based in Dubai, is a pioneer in AI-driven engineering, leveraging physics-based computational systems to design next-generation aerospace hardware.</p><p>As part of the agreement, LEAP 71 will create the complete propulsion stack for Aspire’s rockets using Noyron, its proprietary Large Computational Engineering Model. The first-stage engines will be based on the company’s XRB-2E6 reference design — a high-performance, reusable liquid methane/liquid oxygen (Methalox) engine producing 2,000 kilonewtons of thrust, placing it in the same performance class as top-tier U.S. launch systems.</p><p>Aspire Space is relocating its primary operations to the United Arab Emirates to support the country’s growing ambitions to become a leader in the emerging space economy.</p><p>Stan Rudenko, CEO of Aspire, commented: “Sovereign access to space and rapid reusability are foundational to participating in one of the world’s most dynamic and aspirational sectors. LEAP 71 gives us direct access to propulsion systems right here in the UAE — a strategic advantage that made relocating our entire team an easy decision. We are excited to help the Emirates take a bold next step as a spacefaring nation.”</p><p>Josefine Lissner, CEO of LEAP 71, said: “Engineering lies at the core of human civilization, and we founded LEAP 71 to accelerate engineering itself — to push real-world progress forward using computational systems. But it needs the hard-won knowledge of industry veterans to be meaningful. We are opening up that treasure trove of experience by working with Aspire’s team.”</p><p>LEAP 71’s Noyron Large Computational Engineering Model distills advanced engineering logic, physics models, manufacturing constraints, and practical feedback into a coherent system that generates manufacturable space hardware without human intervention. It’s been called the first “AI that builds machines.” Rather than generative, probabilistic AI systems, it relies on a deterministic scientific foundation rooted in first principles.</p><p>Lin Kayser, Co-Founder of LEAP 71, added: “Innovation requires iteration — but human-driven design of complex machines takes enormous amounts of manual work. By systematically translating the body of knowledge of a field of engineering to Noyron, we radically reduce iteration time from months to days. The next generation of space systems won’t be drawn by humans — they’ll be computed.”</p><p>Over the past year, LEAP 71 has, on average, completed and hot-fired a new rocket engine design every 30 days, including a working aerospike — one of the most complex types of rocket propulsion systems ever tested.</p><p>Sergey Sopov, CTO of Aspire, noted: “For decades, my team and I built rockets the old way — reliable, but slow. Now begins a new era. What LEAP 71 offers is the ability to finally turn our expertise into code, paving the way for rapid development with constant iterations. That’s how we will advance humanity in the New Space Age.”</p><p>In addition to the orbital launcher, Aspire Space is developing a reusable spacecraft capable of transporting up to 2 metric tons of payload to and from orbital stations.</p><p>Hot-fire testing of the propulsion system is scheduled to begin in Q3 2026, starting with the 200 kN second-stage engine.</p><p>The inaugural flight of the Aspire Space launch system is slated for 2030.</p><h4>About Aspire Space</h4><p>Aspire Space is developing a next-generation rapidly reusable space transportation system, comprising a large reusable launcher and a reusable spaceship.</p><p>The R1 two-stage MethaLOX-powered launcher has a capacity up to 15t to LEO.</p><p>The S1 spaceship is capable of delivering 2 tonnes to LEO space stations and back to Earth.</p><p>As a next iteration Aspire Space plans to merge the launcher and spaceship into a fully reusable two-stage Rocketship — one of the most advanced and versatile space launch systems in the world.</p><p>Founded by a team of space pioneers who led the prominent projects such as Zenit, Soyuz and Sea Launch, Aspire Space aims to advance humanity to the New Space Age by providing cutting-edge launch and space transportation services.</p><p>Visit the Aspire Space website for more information.</p><h4>About LEAP 71</h4><p>LEAP 71 was founded on the vision that radically accelerating real-world engineering is essential to shaping the future of humankind. Strategically based in Dubai, UAE, the company works with customers around the globe to design advanced machinery in fields such as aerospace, electric mobility, robotics, and thermal systems.</p><p>A pioneer in the emerging field of Computational Engineering, LEAP 71 designs physical objects autonomously — without human intervention. At its core is Noyron, a Large Computational Engineering Model that encodes logic, physics, production methodologies, and real-world feedback into a coherent, deterministic system. It has been called “the first AI that builds machines.”</p><p>Noyron generates functional designs in seconds or minutes, optimized for modern manufacturing technologies such as industrial 3D printing.</p><p>A key focus for the company is enabling access to space. LEAP 71 is developing a spectrum of reference designs for space propulsion systems that serve as the DNA for customer-specific engines. Frequent physical testing and validation are used to continuously enrich Noyron’s models.</p><p>LEAP 71 was founded in 2023 by aerospace engineer Josefine Lissner and serial entrepreneur Lin Kayser.</p><p>Visit the LEAP 71 website for more information.</p></article>"
            },
            {                outlet: "Government of Dubai Media Office",
                date: "11 JUN 2025",
                title: "Hamdan bin Mohammed explores future of space sector with leading UAE-based startups.",
                badge: "Government of Dubai Media Office",
                url: "https://mediaoffice.ae/en/news/2025/june/11-06/hamdan-bin-mohammed-explores-future-of-space-sector-with-leading-uae-based-startups",
                fileId: "1G_cGlZ7kYrKKfA2rFfxlE6HuMfPay2L_",
                imageData: "assets/images/press/1G_cGlZ7kYrKKfA2rFfxlE6HuMfPay2L_.jpg",
                rows: [["OUTLET", "Government of Dubai Media Office"], ["DATE", "11 JUN 2025"]],
                articleHtml: "<article class=\"media-article\"><p>His Highness Sheikh Hamdan bin Mohammed bin Rashid Al Maktoum, Crown Prince of Dubai, Deputy Prime Minister and Minister of Defence of the UAE, and Chairman of the Supreme Space Council, met with representatives of leading space sector startups operating in the UAE. The meeting is part of His Highness’s keenness to advance the national space ecosystem and further promote its role as a global leader in the space industry.</p><p>His Highness underscored the importance of strong partnerships and strategic collaboration between the public and private sectors as a foundation for developing an advanced and innovative space ecosystem. He highlighted that continuous innovation and long-term investment in future technologies are essential to this progress.</p><p>Sheikh Hamdan also expressed confidence in the capabilities of UAE-based companies and entrepreneurs, noting their crucial role in driving the growth of the local space industry and strengthening the country’s position as a leading global hub in this strategic field.</p><p>His Highness also highlighted the space sector as a vital driver of the future and sustainable economic growth. He stressed the UAE’s ongoing efforts to build a supportive environment that fosters the growth of national companies and unlock new opportunities for investment and innovation, boosting the country’s global competitiveness and leadership in space.  The private sector is leading the space scene in the UAE, reaffirming the maturity of national investments that have been established over the past three decades.</p><p>A number of UAE based companies  took part in the meeting, representing a wide range of specialisations, including locally developed Internet of Things (IoT) solutions, artificial intelligence and remote sensing, commercial space ecosystem development, edge computing for robotics applications, high-resolution Earth observation via micro satellites, as well as AI systems, robotics, interactive simulation technologies, and reusable space launch systems.</p><p>Participants shared insights into their current projects, long-term strategies, and future investment plans in support of the national economy. Discussions focused on strengthening public-private collaboration, expanding operations both locally and internationally, and exploring promising opportunities within the UAE’s growing space sector—highlighting the private sector’s central role in shaping a globally competitive and integrated space industry.</p><p>Company representatives reaffirmed their commitment to the UAE’s space ambitions and outlined plans to expand their operations within the country. They praised the UAE’s flexible regulatory framework and advanced infrastructure as key enablers of sustained investment. Attendees also welcomed initiatives such as the Space Economic Zones Programme, which they said play a vital role in enabling collaboration and fostering long-term, sustainable growth across the space ecosystem.</p><p>The meeting was attended by Dr. Ahmad Belhoul Al Falasi, Minister of Sports, Secretary-General of the Supreme Space Council, and Chairman of the Board of Directors of the UAE Space Agency; Khalid Al Awadi, founder of Rimal; Ibrahim Al Obaidly, founder of Ardhiyat Al Ibdaa Information Solutions; David Critchley, CEO of 4EI; Dr. Hamdullah Mohib, CEO of Marlan Space; Alex Lapir, CEO of Aliensense; Abdulhalim Jallad, co-founder of Oryx Space; and Stan Rudenko, CEO of Aspire Space Technology.</p></article>"
            }
        ];

        function escapeMediaText(value) {
            return String(value ?? '')
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#039;');
        }

        function createMediaMegaCard(item, index) {
            const imageUrl = item.imageData ||
                `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1200`;
            const fallbackLabel = item.outlet
                .split(/\s+/)
                .map(part => part[0] || '')
                .join('')
                .slice(0, 4)
                .toUpperCase();

            return `
                <button
                    type="button"
                    class="media-mega-card"
                    data-open-update="${index}"
                    aria-label="${escapeMediaText(item.outlet + ': ' + item.title)}"
                >
                    <img
                        src="${imageUrl}"
                        alt=""
                        loading="lazy"
                        referrerpolicy="no-referrer"
                        onerror="this.style.display='none'"
                    />
                    <div class="media-mega-fallback" aria-hidden="true">${escapeMediaText(fallbackLabel)}</div>

                    <div class="media-mega-card-content">
                        <div class="media-mega-card-meta">
                            <span class="media-mega-card-outlet">${escapeMediaText(item.outlet)}</span>
                            <span>${escapeMediaText(item.date || 'PUBLICATION')}</span>
                        </div>

                        <h3>${escapeMediaText(item.title)}</h3>
                        <span class="media-mega-card-link">OPEN IN UPDATES ↗</span>
                    </div>
                </button>
            `;
        }

        function initMediaMegaMarquee() {
            const track = document.getElementById('mediaMegaTrack');
            if (!track || !Array.isArray(MEDIA_RELEASES) || MEDIA_RELEASES.length === 0) return;

            const groupMarkup = MEDIA_RELEASES.map((item, index) => createMediaMegaCard(item, index)).join('');

            track.innerHTML = `
                <div class="media-mega-group">${groupMarkup}</div>
                <div class="media-mega-group" aria-hidden="true">${groupMarkup}</div>
            `;

            track.querySelectorAll('[data-open-update]').forEach(button => {
                button.addEventListener('click', () => {
                    const index = Number(button.getAttribute('data-open-update'));
                    openModal('media-modal');
                    requestAnimationFrame(() => {
                        if (typeof window.showMediaArticle === 'function') window.showMediaArticle(index);
                    });
                });
            });
        }

        function initMediaExplorer() {
            const list = document.getElementById('mediaList');
            const stage = document.getElementById('mediaStage');
            const idle = document.getElementById('mediaIdle');
            const articlePane = document.getElementById('mediaArticlePane');
            const articleScroll = document.getElementById('mediaArticleScroll');
            const chromeTitle = document.getElementById('mediaChromeTitle');
            const title = document.getElementById('mediaTitle');
            const heroImage = document.getElementById('mediaHeroImage');
            const heroAmbient = document.getElementById('mediaHeroAmbient');
            const heroFallback = document.getElementById('mediaHeroFallback');
            const text = document.getElementById('mediaText');
            const resetButton = document.getElementById('mediaResetButton');

            function setSelectedButton(index) {
                list.querySelectorAll('button[data-media-index]').forEach(button => {
                    const selected = Number(button.dataset.mediaIndex) === index;
                    button.classList.toggle('is-active', selected);
                    button.setAttribute('aria-current', selected ? 'true' : 'false');
                });
            }

            function resetMediaExplorer() {
                setSelectedButton(-1);
                stage.classList.remove('has-article');
                idle.classList.remove('hidden');
                articlePane.classList.add('hidden');
                heroImage.removeAttribute('src');
                heroAmbient.removeAttribute('src');
                title.textContent = 'Select Update';
                if (chromeTitle) chromeTitle.textContent = '';
                articleScroll.scrollTop = 0;
                mediaTransfer.reset();

                requestAnimationFrame(() => {
                    if (window.mediaSilverWorldMap) window.mediaSilverWorldMap.resize();
                });
            }

            function mediaGeo(item, index) {
                if (item && item.outlet === '24KZ') return 'UAE';
                return MEDIA_GEOTAGS[index] || '';
            }

            function showMedia(index) {
                const item = MEDIA_RELEASES[index];
                if (!item) return;

                setSelectedButton(index);

                stage.classList.add('has-article');
                idle.classList.add('hidden');
                articlePane.classList.remove('hidden');

                title.textContent = item.title;
                if (chromeTitle) chromeTitle.textContent = item.title;

                const imageUrl = item.imageData ||
                    `https://drive.google.com/thumbnail?id=${encodeURIComponent(item.fileId)}&sz=w1800`;

                heroFallback.textContent = item.outlet;
                heroFallback.classList.remove('hidden');
                heroImage.alt = `${item.outlet}: ${item.title}`;
                heroImage.onload = () => heroFallback.classList.add('hidden');
                heroImage.onerror = () => {
                    heroImage.removeAttribute('src');
                    heroAmbient.removeAttribute('src');
                    heroFallback.classList.remove('hidden');
                };
                heroImage.src = imageUrl;
                heroAmbient.src = imageUrl;

                const geo = mediaGeo(item, index);
                const dateline = `<p class="media-article-dateline">${item.date}${geo ? ' \u00b7 ' + geo : ''}</p>`;

                text.innerHTML =
                    item.articleHtml ||
                    `<article class="media-article">${
                        (item.text || []).map(paragraph => `<p>${paragraph}</p>`).join('')
                    }</article>`;

                const articleRoot = text.querySelector('.media-article') || text;
                articleRoot.insertAdjacentHTML('afterbegin', dateline);

                if (item.url) {
                    let host = item.url;
                    try { host = new URL(item.url).hostname.replace(/^www\./, ''); } catch (e) {}
                    (text.querySelector('.media-article') || text).insertAdjacentHTML('beforeend',
                        `<p class="media-article-source"><a class="media-article-source-link" href="${item.url}" target="_blank" rel="noopener">Read the original on ${host} \u2197</a></p>`);
                }

                articleScroll.scrollTop = 0;
                triggerBodyEnter('#mediaText');
            }

            function selectMedia(button, index, immediate) {
                const item = MEDIA_RELEASES[index];
                if (!item || !button) return;
                selectCatalogueItem(mediaTransfer, list, button, index, item.title, () => showMedia(index), !!immediate);
            }

            window.showMediaArticle = function (index) {
                const button = list.querySelector('button[data-media-index="' + index + '"]');
                if (button) selectMedia(button, index, false);
            };

            MEDIA_RELEASES.forEach((item, index) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.dataset.mediaIndex = String(index);
                button.className = 'media-index-item media-update-rubricator';
                button.innerHTML = `
                    <span class="media-index-item-title">${item.title}</span>
                    <span class="media-index-item-arrow" aria-hidden="true">\u2197</span>
                `;
                button.addEventListener('click', () => selectMedia(button, index, false));
                list.appendChild(button);
            });

            resetButton?.addEventListener('click', resetMediaExplorer);

            window.resetMediaExplorer = resetMediaExplorer;
            resetMediaExplorer();
        }

        initMediaExplorer();
        initMediaMegaMarquee();


        const MISSION_FILES = [
            {
                        "title": "The future of space transportation, and why we are building Oryx",
                        "text": [
                                    "Humanity’s destiny is beyond Earth.",
                                    "More paths must open toward that future.",
                                    "From 2000 through 2025, 2,812 orbital launch attempts were recorded worldwide. Look at those numbers alone and access to space appears to be expanding at extraordinary speed.",
                                    "At first glance, the world seems to have no shortage of rockets. Look more closely and a different picture emerges. The United States, China and Russia accounted for 81.7 percent of them. Including Europe, the established launch systems represented almost 90 percent of global activity.",
                                    "Each of these systems is legitimate. Each reflects decades of investment, institutional knowledge and national priorities. However, together they have a structural limit.",
                                    "Last year the world launched more than ever, but most mature launch capacity belongs to a small number of national industrial systems or vertically integrated corporations. Much of that capacity exists to serve domestic programmes, defence missions, institutional priorities or constellations owned by the launch provider or one of its largest customers.",
                                    "High launch activity does not mean that capacity is available when customers need it. Manifests for proven vehicles are often committed years in advance, particularly for dedicated missions and payloads with specific orbital requirements. A spacecraft may be ready long before a suitable launch slot becomes available. Delays then affect more than the mission itself cuz teams remain employed, hardware stays in storage, financing is tied up, and the commercial opportunity may move on.",
                                    "Launch activity is growing faster than the number of genuinely independent routes to orbit. A market can have hundreds of launches and still leave many customers with few practical choices.",
                                    "That is the limit Aspire was created to overcome."
                        ]
            },
            {
                        "title": "Why access concentrates",
                        "text": [
                                    "Launch markets naturally favour the systems already in operation. Governments reinforce this advantage because launch is strategic infrastructure. Vertical integration can concentrate it further: a provider may fly frequently while reserving much of its capacity for its own constellations or orbital platforms.",
                                    "Over time, dependence forms around more than the vehicle. Payload interfaces, integration procedures, insurance, procurement and supply chains adapt to the systems already flying. Launch activity can grow while practical choice remains narrow.",
                                    "A durable space economy therefore needs more than higher cadence through the same gateways. It needs additional vehicles, jurisdictions and industrial chains."
                        ]
            },
            {
                        "title": "A system must serve the market that exists",
                        "text": [
                                    "Thousands of payloads are already being developed around existing mission profiles. Communications satellites, Earth-observation platforms, scientific spacecraft, national security systems and technology demonstrators need predictable access now.",
                                    "Small spacecraft still dominate numerically, but demand is moving towards larger and more capable platforms in several constellation categories.",
                                    "A useful new gateway therefore has to connect two economies.",
                                    "It must serve payloads that organisations already know how to build, fund and operate. It must also create room for missions that become possible only when transportation changes.",
                                    "The next space economy will require transport for commercial stations, autonomous laboratories, servicing spacecraft, manufactured materials, biological samples and eventually people. These missions will have different operating cycles, integration requirements and relationships with Earth.",
                                    "The launch system has to meet the present market while making the next one possible."
                        ]
            },
            {
                        "title": "Launch is only half the journey",
                        "text": [
                                    "Most space transportation remains one-way.",
                                    "A launch vehicle carries a spacecraft upward. The upper stage completes its work and is discarded. The payload remains in orbit, manoeuvres using its own propulsion or eventually re-enters the atmosphere.",
                                    "That model works for communications, navigation and observation spacecraft built to remain in space.",
                                    "It is incomplete for industries that need regular movement between Earth and orbit. Its current areas include pharmaceuticals, advanced materials, tissue engineering, biomanufacturing and semiconductor-related research.",
                                    "These activities do not end when a payload reaches orbit.",
                                    "A pharmaceutical process must return its product. A biological experiment must return samples for analysis. An orbital factory must deliver what it manufactures. A station must receive equipment and supplies. Hardware must be repaired, replaced or recovered. People must travel in both directions.",
                                    "Upmass creates activity in orbit. Downmass connects that activity to customers, laboratories and markets on Earth.",
                                    "Today, that connection remains narrow.",
                                    "Dragon can return up to 3,000 kilograms and is currently the only flying spacecraft able to return significant quantities of cargo from orbit. Smaller systems are emerging. Varda, for example, has begun returning dedicated capsules carrying materials and experimental hardware.",
                                    "That is real progress, but it is not yet a broad transportation network.",
                                    "The future orbital economy needs a complete cycle:",
                                    "launch, orbital operation, return, recovery and the next mission."
                        ]
            },
            {
                        "title": "Full reuse changes more than launch price",
                        "text": [
                                    "Reusability is usually discussed as a way to avoid throwing away expensive hardware.",
                                    "That is only its first effect.",
                                    "A vehicle that loses a first stage on every mission must manufacture another stage for every subsequent mission. Increasing flight frequency therefore requires increasing the production of structures, engines, tanks, valves, fluid systems, avionics and separation hardware. Each new article must be assembled, inspected and accepted for flight.",
                                    "Recovering the booster removes a large part of that manufacturing burden. Recovering the orbital stage removes another.",
                                    "Full reuse changes the relationship between flight rate and factory output. A higher cadence no longer requires an equivalent increase in the production rate of entire vehicles. Manufacturing can shift progressively from replacing flight hardware towards producing a fleet, spares and improvements.",
                                    "It also changes how a launch system learns.",
                                    "An expendable stage transmits telemetry and disappears. Engineers can study the data, but the physical evidence is gone.",
                                    "A returning vehicle brings back heat-affected surfaces, seals, structural joints, engines, valves, wiring and components that have experienced the real mission. Engineers can measure wear, examine damage and compare the vehicle’s physical condition with the models used to design it.",
                                    "A reusable flight returns the machine and the evidence.",
                                    "That evidence matters because simulation is always an approximation. Thermal loads, vibration, combustion behaviour, material fatigue and interactions between subsystems do not reveal every consequence until hardware operates under real conditions.",
                                    "With a returning vehicle, each flight can become part of the design process. Inspection informs the model. The model changes the next configuration. The next flight tests the change.",
                                    "The vehicle becomes both transport and an engineering phase of development."
                        ]
            },
            {
                        "title": "Experience made computational",
                        "text": [
                                    "Aspire’s programme begins with experience accumulated through major launch and transportation systems.",
                                    "That history matters because reusable space transportation is not a single-technology problem. It requires propulsion, structures, aerodynamics, thermal protection, flight control, ground operations, integration and recovery to work as one system.",
                                    "Experience alone, however, is difficult to scale.",
                                    "Much of the most valuable engineering knowledge in any mature programme exists across drawings, calculations, test reports, unwritten conventions and the judgement of individual engineers. When teams disperse, part of that knowledge becomes inaccessible. When a new programme begins, decisions are often reconstructed manually.",
                                    "Computational engineering offers another path. It encodes engineering logic, physical models, manufacturing constraints and data within one computational framework. Observations from simulations and physical tests can be returned to the model and used to change later iterations.",
                                    "The purpose is not to replace engineering judgement with an AI-generated shape.",
                                    "It is to make engineering knowledge executable.",
                                    "A physical requirement becomes part of the model. A manufacturing constraint changes the geometry before production. A test result corrects an assumption. The next configuration carries those corrections forward instead of leaving them isolated in a report.",
                                    "This approach has already produced Aspire’s first major propulsion article. The XRA-2E5 is a one-metre-class methalox aerospike designed for 200 kilonewtons of thrust and manufactured through large-format metal additive production. The full-scale engine was completed in 2026 and is scheduled to proceed through acceptance checks and hot-fire testing. It is hardware awaiting validation, not a proven flight engine.",
                                    "That distinction matters.",
                                    "Computational engineering does not remove the need for testing. It makes each test more valuable because the result can modify the system that generated the design.",
                                    "Programme experience becomes more useful when it can be formalised, tested and reused."
                        ]
            },
            {
                        "title": "Why the entire Oryx system returns",
                        "text": [
                                    "Oryx is designed as a two-stage, fully reusable transportation system.",
                                    "The R1v5 booster provides the first stage of ascent and returns to Earth. D3 continues as the orbital stage and spacecraft. It deploys payloads, supports operations in orbit, returns valuable cargo and lands for another mission.",
                                    "Both stages are preserved.",
                                    "This architecture is more difficult than recovering only the booster. The orbital stage must perform several roles normally divided among separate vehicles. It has to function as a launch stage, an orbital spacecraft and a returning vehicle. It must survive ascent, vacuum operations, atmospheric entry and landing without carrying so much recovery hardware that the system loses its usefulness.",
                                    "But the difficulty follows from the mission.",
                                    "A transport system built only to place payloads in orbit solves the problem inherited from the first space age.",
                                    "A transport system built for a permanent orbital economy has to complete the journey.",
                                    "Aspire describes Oryx as capable of spacecraft deployment, station resupply, autonomous orbital laboratory operations and cargo return, with later development extending towards crewed and lunar missions. The architecture targets reusable operation of both stages rather than treating the orbital stage as expendable hardware.",
                                    "This is why we use the word rocketship.",
                                    "A rocket completes ascent.",
                                    "A rocketship completes the mission and returns."
                        ]
            },
            {
                        "title": "Why now",
                        "text": [
                                    "Several developments have arrived at the same time.",
                                    "Launch demand has reached record levels, but much of the new volume is concentrated in vertically integrated corporations and national systems. Commercial stations are moving from concepts towards procurement and construction. In-space production is progressing from isolated experiments towards repeated missions and commercial validation. Returning capsules are proving that materials can be processed in orbit and delivered back to Earth.",
                                    "Metal additive manufacturing can now produce propulsion hardware at scales and levels of geometric complexity that were previously impractical. Computational engineering can encode physical and manufacturing logic in a reusable model rather than creating each design through a separate manual process.",
                                    "At the same time, countries outside the traditional centres of launch power are seeking a larger role in the space economy. They do not all need to reproduce the national programmes of the United States, China, Europe, India or Russia. They need credible ways to participate in the infrastructure that connects Earth with orbit.",
                                    "This creates an opening for a different kind of programme.",
                                    "One that draws on the engineering experience of earlier launch systems without inheriting their institutional boundaries.",
                                    "One that combines modern manufacturing and computational engineering with a fully reusable architecture.",
                                    "One that serves current spacecraft while preparing for missions that require orbital work and return.",
                                    "One that adds an independent route to orbit instead of asking the world to depend on the same small number of gateways."
                        ]
            },
            {
                        "title": "Why we are building Aspire",
                        "text": [
                                    "We will build industries in orbit, establish permanent settlements beyond our planet, draw on new resources and make discoveries impossible under terrestrial conditions. The scale and form of that future remain uncertain. The need for transportation does not.",
                                    "No civilisation expands without routes.",
                                    "Those routes determine more than the price of moving cargo. They determine who can participate, which industries can emerge, what laws become practical and where power accumulates.",
                                    "The first era of spaceflight was built around national programmes and singular missions. The current era is being shaped by a small number of state-backed and vertically integrated systems. They have driven the industry forward, but they should not become its final structure.",
                                    "The next era needs more gateways and more complete transportation. It’s time to build."
                        ]
            }
];

        function initMissionExplorer() {
            const countEl = document.getElementById('missionCount');
            const listEl = document.getElementById('missionList');
            const idleEl = document.getElementById('missionIdleState');
            const articleEl = document.getElementById('missionArticlePane');
            const backBtn = document.getElementById('missionBackButton');
            const homeBtn = document.getElementById('missionHomeButton');
            const titleEl = document.getElementById('missionTitle');
            const textEl = document.getElementById('missionText');
            const stageEl = document.getElementById('missionStage');

            function selectMission(button, idx, immediate) {
                const item = MISSION_FILES[idx];
                if (!item || !button) return;
                selectCatalogueItem(missionTransfer, listEl, button, idx, item.title, () => openMissionArticle(idx), !!immediate);
            }

            function renderMissionIndex() {
                listEl.innerHTML = '';
                MISSION_FILES.forEach((item, idx) => {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'media-index-item mission-index-item media-update-rubricator';
                    button.innerHTML = `
                        <span class="media-index-item-title">${item.title}</span>
                        <span class="media-index-item-arrow" aria-hidden="true">↗</span>
                    `;
                    button.addEventListener('click', () => selectMission(button, idx, false));
                    listEl.appendChild(button);
                });
                if (countEl) countEl.textContent = String(MISSION_FILES.length).padStart(2,'0');
            }

            function openMissionArticle(index) {
                const item = MISSION_FILES[index];
                if (!item) return;
                idleEl.classList.add('hidden');
                articleEl.classList.remove('hidden');
                stageEl?.classList.add('has-article');
                titleEl.textContent = item.title;
                textEl.innerHTML = item.text.map(paragraph => `<p>${paragraph}</p>`).join('');

                Array.from(listEl.querySelectorAll('.media-index-item')).forEach((node, idx) => {
                    node.classList.toggle('is-active', idx === index);
                });
                const scroll = document.getElementById('missionArticleScroll');
                if (scroll) scroll.scrollTop = 0;
                triggerBodyEnter('#missionText');
            }

            function resetMissionExplorer() {
                articleEl.classList.add('hidden');
                idleEl.classList.remove('hidden');
                stageEl?.classList.remove('has-article');
                Array.from(listEl.querySelectorAll('.media-index-item')).forEach(node => node.classList.remove('is-active'));
                missionTransfer.reset();
            }

            backBtn?.addEventListener('click', resetMissionExplorer);
            homeBtn?.addEventListener('click', resetMissionExplorer);
            window.resetMissionExplorer = resetMissionExplorer;
            window.resizeMissionCanvas = () => { if (window.missionStageWorldMap) window.missionStageWorldMap.resize(); };
            renderMissionIndex();
            resetMissionExplorer();
            window.addEventListener('resize', window.resizeMissionCanvas);
        }

        initMissionExplorer();

        /* ============================================================================
           SYSTEM ARCHITECTURE — same catalogue -> top-slot -> Transfer Band
           interaction as Mission and Updates. Specifications are the supplied
           brief, composed as labelled spec groups rather than loose paragraphs.
           ============================================================================ */
        function initArchitectureExplorer() {
            const list = document.getElementById('oryxList');
            const stage = document.getElementById('oryxStage');
            const text = document.getElementById('oryxText');
            if (!list || !stage || !text) return;

            const ARCHITECTURE_ENTRIES = [
                {
                    id: 'sys-rocketship',
                    name: 'ORYX ROCKETSHIP',
                    image: 'assets/images/system/R1V5.avif',
                    imageAlt: 'Oryx Rocketship',
                    html: `
                        <p class="architecture-spec-lead">Reusable first and second stages</p>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">PAYLOAD MASS</div>
                            <p>LEO \u2014 H=200 km, i=51.6\u00b0</p>
                            <p>up to 5 t fully reusable</p>
                        </div>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">PROPULSION</div>
                            <p><span class="architecture-spec-sublabel">First stage</span>5 engines \u00d7 1,000 kN / 225,000 lbf</p>
                            <p><span class="architecture-spec-sublabel">Second stage</span>5 engines \u00d7 200 kN / 45,000 lbf</p>
                        </div>`
                },
                {
                    id: 'stage-d3',
                    name: 'D3 CARGO SPACESHIP',
                    image: 'assets/images/system/S2_5.avif',
                    imageAlt: 'D3 Cargo Spaceship',
                    html: `
                        <p class="architecture-spec-lead">Reusable second stage, first of the kind</p>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">UP TO 3 T</div>
                            <p>to LEO and return to Earth</p>
                        </div>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">CAPABILITIES</div>
                            <ul class="architecture-spec-list">
                                <li>Stations refuel and manoeuver</li>
                                <li>Standalone orbital lab</li>
                                <li>Future crew missions</li>
                                <li>Future Moon missions</li>
                            </ul>
                        </div>`
                },
                {
                    id: 'aspire-launcher',
                    name: 'ASPIRE LAUNCHER',
                    image: 'assets/images/system/Fairings_2.avif',
                    imageAlt: 'Aspire Launcher',
                    html: `
                        <p class="architecture-spec-lead architecture-spec-kicker">R1 TWO-STAGE MEDIUM-LIFT LAUNCHER</p>
                        <p class="architecture-spec-intro">Two-stage medium-lift space launch vehicle</p>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">LEO</div>
                            <p>H=200 km, i=51.6\u00b0</p>
                        </div>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">PAYLOAD</div>
                            <p>15 t reusable</p>
                            <p>17 t expendable</p>
                        </div>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">REUSABILITY</div>
                            <p>Reusable first stage and fairing leading to lower operating costs</p>
                        </div>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">PROPULSION</div>
                            <p>Green methane-oxygen engines optimized for reusability</p>
                        </div>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">STRUCTURE</div>
                            <p>Composite second stage with high mass ratio</p>
                        </div>
                        <div class="architecture-spec-group">
                            <div class="architecture-spec-label">FAIRING</div>
                            <p>First in class reusable fairing for launching satellites</p>
                        </div>`
                }
            ];

            function showArchitectureEntry(index) {
                const entry = ARCHITECTURE_ENTRIES[index];
                if (!entry) return;
                stage.classList.add('has-article');
                const visual = entry.image
                    ? `<figure class="architecture-spec-visual"><img src="${entry.image}" alt="${entry.imageAlt || entry.name}"></figure>`
                    : '';
                text.innerHTML = `<div class="architecture-spec-layout">${visual}<div class="architecture-spec-copy">${entry.html}</div></div>`;
                list.querySelectorAll('button[data-architecture-index]').forEach(button => {
                    const active = Number(button.dataset.architectureIndex) === index;
                    button.classList.toggle('is-active', active);
                    button.setAttribute('aria-current', active ? 'true' : 'false');
                });
                const scroll = stage.querySelector('.media-article-scroll');
                if (scroll) scroll.scrollTop = 0;
                triggerBodyEnter('#oryxText');
            }

            function selectArchitecture(button, index, immediate) {
                const entry = ARCHITECTURE_ENTRIES[index];
                if (!entry || !button) return;
                selectCatalogueItem(architectureTransfer, list, button, index, entry.name, () => showArchitectureEntry(index), !!immediate);
            }

            ARCHITECTURE_ENTRIES.forEach((entry, index) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.dataset.architectureIndex = String(index);
                button.className = 'media-index-item architecture-rubricator';
                button.innerHTML = `<span class="media-index-item-outlet taxonomy-index-name">${entry.name}</span><span class="media-index-item-arrow" aria-hidden="true">\u2197</span>`;
                button.addEventListener('click', () => selectArchitecture(button, index, false));
                list.appendChild(button);
            });

            const first = list.querySelector('button[data-architecture-index="0"]');
            if (first) selectArchitecture(first, 0, true);
        }

        initArchitectureExplorer();


    

/*
 * Silver Dither World Map
 * Изолированный WebGL-слой карты из oryx_architecture (2).html.
 * Никакая другая архитектура, верстка или логика исходного сайта не включена.
 */
(function (global) {
  'use strict';

  const LAND_MASK = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADP////wAAB//////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//////B/9/3////jAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOP////+H/////////v/8AAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf+AP//4////////////gAAAAAAADOAAAAAfAAAAAAAAAB/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH/9///4B///////////AAAAAAAY4/8AAAAAAAAAAAAAAAP/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAP/H/8AH///////////gAAAAAAP/8AAAAAAAAAAAAAAAAAfzgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAfzw/f//D////////////wAAAAAAA/4IAAAAAAAAAAAAAAAAAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHgAAHAHf+AH///////////8AAAAAAAB4PAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/gAAADwH//gB////////////wAAAAAAAMAAAAAAAAAAAAAAAAAAAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA+HBwD+B4ADAAH///////////gAAAAAAAAAAAAAAAAAAD/gAAAAAAP//+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH/HwngPw/gAAAAP////////8AAAAAAAAAAAAAAAAAA/4AAAAAD/////wAAAAB/8AAAAAAAAAAAAAAAAAAAAAAAB+AAB5//8AAAAA////////+AAAAAAAAAAAAAAAAAB/AAAAAAf/////gAAAAAP+DwAAAAAAAAAAAAAAAAAAAH/gAAAAAAAAAAAAAH///////+AAAAAAAAAAAAAAAAAA+AAAAAAH/////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//AA4Pz8OHfAAAAA////////wAAAAAAAAAAAAAAAAAeAAAAAH///////v4H4AAHwAAAAAAAAAAAAAAAAAAAAA/97k8N84P/4AAAAAD///////wAAAAAAAAAAAAAAAAAfAAA+IB///////////gABgAAAAAAAAAAAAAAAAAAAAAf5//3g/sD///gAAAB///////4AAAAAAAAAAAAAAAAAPgAAPjff//////////4AA//4AAAAAADgAAAAAAAAAAAA8P//4Bnw////wAAAD///////gAAAAAAAAAAAAAAAAD8AAPzv////////////H+///gAAAAABAAAAD/4AAAAAAAD///gB+H////gAAB3/////84AAAAAAAAAAP+AAAAAAgAH+P///////////////////4AAAAAAAAH////gAB3IAf///CfgB/v//AAA///////4AAAAAAAAAD//gAAAAAAAA/n///////////////////+AAOAAAAAH/////4f///h///B8+A/Af/4AAAf/////wAAAAAAAAAD///4AAAAAD8H5//////////////////////z/+wAAf///////////4A8AAP+PwA/4AAAP/////gAAAAAAAAAH////8AAAYO/4/P/////////////////////////gAB///////////+BH+Dv/H8Dj/8AAP////wAAAAAAAAAAH/////4HB/////x/////////////////////////+AAH///////////////////Aw//gAH////wAAAAAAAAAAD//////Bj/////5///////////////////////////gGf/////////////////3AAf//AA////wAAABgAAAAAB////8fif/////9/////////////////////////z/8f//////////////////4AAP+HgAP///AAAP/4AAAAAB//x//wH////////////////////////////////8D4B//////////////////94B//4AAA//+AAAA//AAAAAA//wP/8B/////////////////////////////////AEAAH////////////////+fwcf/gAAP//AAAAH/gAAAAAf/8f//H////////////////////////////////+AAEAB////////////////4PnAA98AAB//wAAAAMAAAAAAf/8P////////////////////////////////////wAAAP////////////////+AAAAHzAAAP/wAAAAAAAAAAA//8P////////////////////////////////////+AAAH////////////////8ABCewHAAAB/4AAAAAAAAAAA//+D/////////////////////////////////z//4AAAD////////////////+AAAH/AAAAAP+AAAAAAAAAAAf//Af///////////////////////////////x5//gAAAAf//33////////////AAAB/+AAAAAPgAAAAAAAAAAH//4P///////////////////////////////wY//AAAAAz//74H///////////gAAAP/gAAAAAwAAAAAAAAAAB///g4H/////////////////////////////wA/wgAAAAAD/4wAB//////////4AAAH/4GAAAAAAAAAAAAAAAAP//wB/////////////////////////////x8A8AAAAAAAAt/AAAH//////////gAAB//jwAAAAAAAAAAAAAAAD4/wB///////////////////////////+AAAAeAAAAAAAAAPAAAAB/////////8AAAP//+AAAAAAAAAAAAAOAAAP8AH///////////////////////////AAAAfAAAAAAAAAHOAAAAP/////////gAAB///wAAAAAAAAAAAAD4AAJ+Ab///////////////////////////AAAAf8AAAAAAAAHAAAAAB//////////wAAf//8AAAAAAAAAAAAA8AAOPgP///////////////////////////gAAAP/AAAAAAAAPAAAAAAP//////////AAP///wAAAAAAAAAAAAPgADPgD///////////////////////////gAAAH/AAAAAAAAMAAAAAAA///////////wH///+AAAAAAAAAAAAB8AAzAA///////////////////////////gAAAB/wAAAAAAAAAAAAAAAP//////////+H////+AAAAAAAAAAAPHgAOAe///////////////////////////+AAAAf4AAAAAAAAAAAAAAAQ///////////g/////gAAAAAAAAAAPg8AD//////////////////////////////3AAAD8AAAAAAAAAAAAAAAEP//////////4P////+AAAAAAAAAAB5/gf////////////////////////////////AAA+AAAAAAAAAAAAAAAAg///////////D/////gAAAAAAAAAA8P8P////////////////////////////////wAAOAAAAAAAAAAAAAAAAAP//////////4/////wAAAAAAAAAAAH/H////////////////////////////////MAADAAAAAAAAAAAAAAAAAB////////////////GAAAAAAAAAAAB/n////////////////////////////////zAAAAAAAAAAAAAAAAAAAAA7/////////////+fjAAAAAAAAAAAAoD////////////////////////////////84AAAAAAAAAAAAAAAAAAAADP////////////8GB4AAAAAAAAAAAAT/////////////////////////////////OAAAAAAAAAAAAAAAAAAAAAd////////////88A/wAAAAAAAAAAAT/////////////////////////////////iAAAAAAAAAAAAAAAAAAAAABP///////////+/AP+AAAAAAAAAAAP/////////////////////////////////4gAAAAAAAAAAAAAAAAAAAAAb////////////fwAFgAAAAAAAAAAA/////////////////////////////////8IAAAAAAAAAAAAAAAAAAAAAD/////////////+AAYAAAAAAAAAAAH////////8///////////////////////+DAAAAAAAAAAAAAAAAAAAAAA//////////////pgAAAAAAAAAAAAA///////4cP///////////////////////AAAAAAAAAAAAAAAAAAAAAAAP//////////////gAAAAAAAAAAAAAP//9///8P3///////////////////////gAAAAAAAAAAAAAAAAAAAAAAD/////////////PAAAAAAAAAAAAAAD//+H//+Bh///////////////////////wGAAAAAAAAAAAAAAAAAAAAAB/////////////DAAAAAAAAAAAAAAA//jw///gAD//////////////////////4B+AAAAAAAAAAAAAAAAAAAAAf////////////AAAAAAAAAAAAAAH//4wfD//wAAf/////////////////////4B/gAAAAAAAAAAAAAAAAAAAAH////////////gAAAAAAAAAAAAAB//8AjwP/4AAB/////////////////////AAbAAAAAAAAAAAAAAAAAAAAAB////////////+AAAAAAAAAAAAAAf//AIfg//AeAf////////////////////gAGAAAAAAAAAAAAAAAAAAAAAAf///////////wAAAAAAAAAAAAAAD//AAB8P/6/8P////////////////////wABgAAAAAAAAAAAAAAAAAAAAAH///////////4AAAAAAAAAAAAAAB//gAwHz0X/////////////////////4/4AAcAAAAAAAAAAAAAAAAAAAAAA///////////+AAAAAAAAAAAAAAAf/wAMAw8D/////////////////////8Z4AAHAAAAAAAAAAAAAAAAAAAAAAP///////////AAAAAAAAAAAAAAAP/8ACAEHg/////////////////////8IPAABwAAAAAAAAAAAAAAAAAAAAAB//////////+gAAAAAAAAAAAAAAB/+AAACA8P/////////////////////AD4AA4AAAAAAAAAAAAAAAAAAAAAAP//////////wAAAAAAAAAAAAAAAP/gAAPAOB/////////////////////5gPAAcAAAAAAAAAAAAAAAAAAAAAAD//////////8AAAAAAAAAAAAAAAGfgA/QQBgf/////////////////////8DwAvAAAAAAAAAAAAAAAAAAAAAAAf//////////AAAAAAAAAAAAAAAAGAf/4AAAAjH///////////////////8A8APwAAAAAAAAAAAAAAAAAAAAAAD//////////wAAAAAAAAAAAAAAABg///AAAAAJ///////////////////8APB/8AAAAAAAAAAAAAAAAAAAAAAA//////////4AAAAAAAAAAAAAAAAf///gAAAAMf///////////////////ADA/8AAAAAAAAAAAAAAAAAAAAAAAB/////////4AAAAAAAAAAAAAAAAP///4AAAAAH///////////////////4AA7wAAAAAAAAAAAAAAAAAAAAAAAAH////////4AAAAAAAAAAAAAAAAP////AAAAAD////////////////////AA7AAAAAAAAAAAAAAAAAAAAAAAAAB////////8AAAAAAAAAAAAAAAAH/////ADAAA////////////////////wAGAAAAAAAAAAAAAAAAAAAAAAAAAAP///////+AAAAAAAAAAAAAAAAB/////8D8AAf///////////////////+ABgAAAAAAAAAAAAAAAAAAAAAAAAADn///////AAAAAAAAAAAAAAAAA//////g/+OH////////////////////gAQAAAAAAAAAAAAAAAAAAAAAAAAAAZ///////wAAAAAAAAAAAAAAAAP//////P///////////////////////4AAAAAAAAAAAAAAAAAAAAAAAAAAAAGP////+DcAAAAAAAAAAAAAAAAD/////////////x/////////////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAT///+BADgAAAAAAAAAAAAAAAB//////////b//8P////////////////gAAAAAAAAAAAAAAAAAAAAAAAAAAAACf//+AAA4AAAAAAAAAAAAAAAA//////////////h////////////////4AAAAAAAAAAAAAAAAAAAAAAAAAAAADx///AAAPAAAAAAAAAAAAAAAA//////////+P//4P///////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAef//wAABwAAAAAAAAAAAAAAAf//////////x///A9//////////////+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAh//8AAAcAAAAAAAAAAAAAAAP//////////8P//4Af//////////////gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMf//AAADAAAAAAAAAAAAAAAH///////////j//+gR//////////////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAADD//gAAAAAAAAAAAAAAAAAAB///////////8f//4MAAf///////////4gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIf/4AAAAQAAAAAAAAAAAAAA////////////H///HgAD///////////8YAAAAAAAAAAAAAAAAAAAAAAAAAAAAABD/+AAAAAAAAAAAAAAAAAAAf///////////wf////AAf//////////+GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQf/gAAHwAAAAAAAAAAAAAAH///////////+H////wAB//////////+BAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/4AACPgAAAAAAAAAAAAAD////////////w////+AA/////n////4AAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAA/+AAwAOAAAAAAAAAAAAAA////////////+P////AAH///8B///4wAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAP/wB8ABwAAAAAAAAAAAAAP////////////j////gAAH///Af//8IAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAD/+AfAAPAAAAAAAAAAAAAB////////////4f///wAAA///gD//+DAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAf/gHwAAD4AAAAAAAAAAAAf///////////+D///8AAAP//gAf//DgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/+H4AACfgAAAAAAAAAAAH////////////gf//+AAAD//wAD//4YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH//+AAcCAAAAAAAAAAAAB////////////+H///AAAA//4AA//+AAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA///AAAAAAAAAAAAAAAAAf////////////g///gAAAP/4AAP//wAAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//wAAAAAAAAAAAAAAAAP////////////8H/+AAAAD/+AADv/+AABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADH8cAAAAAAAAAAAAAAAD/////////////B//AAAAAf8AAAR//wAAYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//wAAAAAAAAAAAAAAA/////////////4f/AAAAAH/AAAAf/+AAGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH/8AAAAAAAAAAAAAAAP/////////////n/AAAAAA/wAAAH//gAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP+AAAAAAAAAAAAAAAD/////////////8/AAAAAAP8AAAB//4AALAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAfgAAAAAAAAAAAAAAA//////////////sAAAAAAD/AAAAM/+AACYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD4AAIAAAAAAAAAAAAP/////////////8AAAAAAAfwAAADD/gAAhAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAeAAOgAAAAAAAAAAAB/////////////+AGAAAAAH8AAAAw/4AAEIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgAf+AAAAAAAAAAAAH/////////////wfgAAAAA/AAAAMH8AAB0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8AH3+6AAAAAAAAAAB///////////////wAAAAAPgAAACAcAAEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADhD9//gAAAAAAAAAAH//////////////8AAAAAByAAAAgGAACCIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAft///8AAAAAAAAAAB///////////////AAAAAAYgAAAMBAAAAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAx////wAAAAAAAAAAf//////////////gAAAAACcAAABgAAAAPwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEf///+AAAAAAAAAAD//////////////4AAAAAAHAAAAYAAAACcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD////wAAAAAAAAAAP/////////////8AAAAAAAwAAADgAACANAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA////+QAAAAAAAAAB//8H//////////AAAAAAAAAAAAcAABgBgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/////gAAAAAAAAAP/4B//////////gAAAAAAAAAAMHgAA+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////8AAAAAAAAAAwAAO/////////wAAAAAAAAAADx4AA/gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//////gAAAAAAAAAAAAAH////////4AAAAAAAAAAAeeAAPgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/////8AAAAAAAAAAAAAA////////+AAAAAAAAAAADzgAH4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//////AAAAAAAAAAAAAAP////////AAAAAAAAAAAAecAP/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//////4AAAAAAAAAAAAAH////////AAAAAAAAAAAAD7AL/wAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//////+AAAAAAAAAAAAAB////////gAAAAAAAAAAAAfAH/+IRgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA///////AAAAAAAAAAAAAAf///////gAAAAAAAAAAAAH4B/+EYYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//////+AAAAAAAAAAAAAH///////4AAAAAAAAAAAAA+Af/iAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH///////8AAAAAAAAAAAAB///////8AAAAAAAAAAAAAHwD/4mAD4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB////////wAAAAAAAAAAAAf//////+AAAAAAAAAAAAAB+Af8OAAOGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf///////+gAAAAAAAAAAAD///////AAAAAAAAAAAAAAPwH/HgAAj4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////////wAAAAAAAAAAAf//////gAAAAAAAAAAAAAB+AfhsC89/4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//////////AAAAAAAAAAAD//////4AAAAAAAAAAAAAAPgAQLAAF//wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//////////4AAAAAAAAAAA//////8AAAAAAAAAAAAAAB4AACYAAH/+AMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH//////////wAAAAAAAAAAH/////+AAAAAAAAAAAAAAAOAAAiAAAP/wUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//////////8AAAAAAAAAAB//////gAAAAAAAAAAAAAAAYAAAAABB//OCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//////////AAAAAAAAAAAP/////8AAAAAAAAAAAAAAAPGAAAAAAf/wAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//////////4AAAAAAAAAAD//////AAAAAAAAAAAAAAAA/4AAAAAH/4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf/////////8AAAAAAAAAAAf/////wAAAAAAAAAAAAAAAAfwAAAAD/DgACAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//////////AAAAAAAAAAAH/////8AAAAAAAAAAAAAAAAAA5wwAADw4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//////////gAAAAAAAAAAB//////AAAAAAAAAAAAAAAAAAAgwAAAAHAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAH/////////4AAAAAAAAAAAf/////4AAAAAAAAAAAAAAAAAAEIAAAAAcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB/////////8AAAAAAAAAAAH//////AAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP////////+AAAAAAAAAAAB//////wAAAAAAAAAAAAAAAAAAAAAQAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////////AAAAAAAAAAAAf/////8AAAAAAAAAAAAAAAAAAAAA/4DAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf////////gAAAAAAAAAAAP//////ABgAAAAAAAAAAAAAAAAAAf8BwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH////////4AAAAAAAAAAAD//////wAYAAAAAAAAAAAAAAAAAAH/AcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA////////+AAAAAAAAAAAB//////8AOAAAAAAAAAAAAAAAAABz/gHwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH////////gAAAAAAAAAAAf//////AHwAAAAAAAAAAAAAAAAA//4B+AAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAA////////4AAAAAAAAAAAH//////gH8AAAAAAAAAAAAAAAAAf//gfgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD///////8AAAAAAAAAAAB//////wH+AAAAAAAAAAAAAAAAAP//8H4AAAACAAMAAAAAAAAAAAAAAAAAAAAAAAAAP///////AAAAAAAAAAAAf/////wB/AAAAAAAAAAAAAAAAAP///z/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB///////wAAAAAAAAAAAH/////4AfwAAAAAAAAAAAAAAAAD/////wAAAAAADAAAAAAAAAAAAAAAAAAAAAAAAAAP//////8AAAAAAAAAAAB/////8AH8AAAAAAAAAAAAAAAAB/////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD///////AAAAAAAAAAAAP////8AB/AAAAAAAAAAAAAAAAA//////gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA///////gAAAAAAAAAAAD////+AAfgAAAAAAAAAAAAAAAB//////+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//////wAAAAAAAAAAAAf////wAH4AAAAAAAAAAAAAAAD///////wAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//////8AAAAAAAAAAAAH////8AD+AAAAAAAAAAAAAAAD///////8AAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//////+AAAAAAAAAAAAA/////gA/AAAAAAAAAAAAAAAB////////gAAAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//////AAAAAAAAAAAAAP////4APwAAAAAAAAAAAAAAA////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////8AAAAAAAAAAAAAD////8AD8AAAAAAAAAAAAAAAP////////gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////8AAAAAAAAAAAAAAf////AA+AAAAAAAAAAAAAAAH////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP////8AAAAAAAAAAAAAAH////AAHgAAAAAAAAAAAAAAA/////////gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH////+AAAAAAAAAAAAAAB////AAAAAAAAAAAAAAAAAAAP////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB/////gAAAAAAAAAAAAAAH///wAAAAAAAAAAAAAAAAAAB/////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////wAAAAAAAAAAAAAAA///4AAAAAAAAAAAAAAAAAAAf////////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP////4AAAAAAAAAAAAAAAP//8AAAAAAAAAAAAAAAAAAAD////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD////8AAAAAAAAAAAAAAAB//+AAAAAAAAAAAAAAAAAAAA/////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA////+AAAAAAAAAAAAAAAAP//gAAAAAAAAAAAAAAAAAAAP////////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP////AAAAAAAAAAAAAAAAD//gAAAAAAAAAAAAAAAAAAAB//8D////4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD////gAAAAAAAAAAAAAAAA//wAAAAAAAAAAAAAAAAAAAAf/wAH///+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA////4AAAAAAAAAAAAAAAAP/wAAAAAAAAAAAAAAAAAAAAP/wAA7///AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP///8AAAAAAAAAAAAAAAAD4AAAAAAAAAAAAAAAAAAAAAD8AAAM///gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH///EAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcAAAAX//4AAAACAAAAAAAAAAAAAAAAAAAAAAAAAAB///4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//8AAAAAwAAAAAAAAAAAAAAAAAAAAAAAAAA///+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH//AAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAP///gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//gAAAAAwAAAAAAAAAAAAAAAAAAAAAAAAAH///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf/4AAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAB///4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA7gAAAAAD8AAAAAAAAAAAAAAAAAAAAAAAAAP/+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA+AAAAAAAAAAAAAAAAAAAAAAAAAH//wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPAAAAAAAAAAAAAAAAAAAAAAAAAB//4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABgAAAAAAAAAAAAAAAAAAAAAAAAAf/kAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA+AAAAAFQAAAAAAAAAAAAAAAAAAAAAAAAAH/8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPgAAAADwAAAAAAAAAAAAAAAAAAAAAAAAACf/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwAAAAB4AAAAAAAAAAAAAAAAAAAAAAAAAAv/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYAAAAA8AAAAAAAAAAAAAAAAAAAAAAAAAAD/4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA+AAAAAAAAAAAAAAAAAAAAAAAAAAD/+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/AAAAAAAAAAAAAAAAAAAAAAAAAAA/+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAfgAAAAAAAAAAAAAAAAAAAAAAAAAAf/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHwAAAAAAAAAAAAAAAAAAAAAAAAAAH/4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB/8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB/wAfAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAC7gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAb8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB8AAAAAAAAAAAAAAAAAAAAAAAAAAB/gAAAAAAEAAD8A/AAAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8AAAAAAAAAAAAAAAAAAAAAAAAAAH/+AAAAAAfyIL////j/////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOAAAAAAAAAAAAAAAAAAAAAAAAAAf//+PgAAH///////////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADwAAAAAAAAAAAAAAAAAAAAAACAD//////gAP////////////////gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA5/AAAAAAAAAAAAAAAAAAAAAAB+H//////4AH//////////////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPf4AAAAAAAAAAAAAAAAAAPAAH////////4B////////////////////gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD3/AAAAAAAAAAAAAAAB/n////////////+A/////////////////////gAAAAAAAAAAAAAAAAAAAAAAAAAAAAP+/4AAAAAAAAAAAGcef///////////////g///////////////////////wAAAAAAAAAAAAAAAAAAAAf4AAAAH/H+AAAAAAAAAAAH//////////////////4f//////////////////////+AAAAAAAAAAAAAAAAAAAARAAEAAAAH/gAAAAAAAAAAH///////////////////////////////////////////AAAAAAAAAAAAAABggAAAH+H/+BsD//8AAAAAAAAAAf///////////////////////////////////////////gAAAAAAAAAAAAAAAAd4AAP////////+AAAAAAAAAAD///////////////////////////////////////////AAAAAAAAAAAAB//////+AA////////4AAAAAAAAAAD//////////////////////////////////////////+AAAAAAAAAAAP//////////////////4AAAAAAAAAAP//////////////////////////////////////////+AAAAAAAAAAAD/////////////////+AAAAAAAAAAP////////////////////////////////////////////gAAAAAAAAAAP////////////////wAAAAAAAAAAD/////////////////////////////////////////////4AAAAAAAAH///////////////////4AAAAAAAAAP//////////////////////////////////////////////AAAAAAADg//////////////////+AAAAAAD+AB///////////////////////////////////////////////+AAAAAAAeA//////////////////gAAAAAB/wAf//////////////////////////////////////////////4AAAAAAAAAAA////////////////+AAAEAB/8AAA/////////////////////////////////////////////gAAAAAAAAAAAH/////////////////gD/gH/4AAAP////////////////////////////////////////////wAAAAAAAAAD+f//////////////////wAAAAAAB//////////////////////////////////////////////+AAAAAAAAAAH/////////////////////gAA/5////////////////////////////////////////////////4AAAAAAAAAAf/////////////////////wf///////////////////////////////////////////////////wAAAAAAAAAP///////////////////////////////////////////////////////////////////////////8AAAAeAAAAP///////////////////////////////////////////////////////////////////////////+AAAAAf////4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAeAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==";
  const VERT = "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
  const FRAG = "\n            precision highp float;\n            uniform vec2 uRes; uniform float uTime;\n            uniform sampler2D uMap; uniform sampler2D uBayer;\n            uniform float uCell;\n            \n            float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\n            float vnoise(vec2 p){vec2 i=floor(p),f=fract(p);\n             f=f*f*f*(f*(f*6.0-15.0)+10.0);\n             return mix(mix(hash(i),hash(i+vec2(1.0,0.0)),f.x),mix(hash(i+vec2(0.0,1.0)),hash(i+vec2(1.0,1.0)),f.x),f.y);}\n            float fbm(vec2 p){float v=0.0,a=0.5;\n             for(int i=0;i<4;i++){v+=a*vnoise(p);p=p*2.02+vec2(11.3,7.7);a*=0.5;}\n             return v;}\n            \n            void main(){\n              vec2 grid = gl_FragCoord.xy/uCell;\n              vec2 cell = floor(grid);\n              vec2 inC  = fract(grid);\n              vec2 cpx  = (cell+0.5)*uCell;\n              vec2 uv   = cpx/uRes;\n              \n              float bandH = (uRes.x/2.0)/uRes.y;\n              vec2 muv = vec2(fract(uv.x + 0.9778), (uv.y - 0.5)/max(bandH, 0.0001) + 0.5);\n              float inBand = step(0.0, muv.y)*step(muv.y, 1.0);\n              \n              float land = texture2D(uMap, muv).r * inBand;\n              \n              vec2 q = vec2(uv.x*3.4, uv.y*2.1);\n              vec2 w = vec2(fbm(q + vec2(0.0, uTime*0.045)), fbm(q + vec2(4.7,2.1) + vec2(uTime*0.038, 0.0)));\n              float flow = clamp(fbm(q*1.25 + w*0.85 + vec2(uTime*0.05, -uTime*0.022))*1.30 - 0.15, 0.0, 1.0);\n              float still = fbm(q*1.25 + vec2(9.1,4.3));\n              \n              float sea = 0.02 + still*0.17;\n              float soil = 0.22 + flow*0.72;\n              float v = mix(sea, soil, land);\n              \n              // Monochrome / Silver metallic map theme\n              vec3 sea_c = vec3(0.03, 0.03, 0.04); \n              vec3 land_c = vec3(0.5, 0.5, 0.55); \n              vec3 col = mix(sea_c, land_c, land);\n              \n              float th = texture2D(uBayer, (mod(cell,8.0)+0.5)/8.0).r;\n              float lvl = clamp(floor(v*5.0 + th)/5.0, 0.0, 1.0);\n              float sz = lvl > 0.0 ? (0.36 + 0.64*lvl) : 0.0;\n              \n              float d = max(abs(inC.x-0.5), abs(inC.y-0.5));\n              float on = step(d, sz*0.42);\n              \n              gl_FragColor = vec4(mix(vec3(0.0), col, on), 1.0);\n            }\n        ";

  const BAYER_8X8 = [
    0,32,8,40,2,34,10,42,
    48,16,56,24,50,18,58,26,
    12,44,4,36,14,46,6,38,
    60,28,52,20,62,30,54,22,
    3,35,11,43,1,33,9,41,
    51,19,59,27,49,17,57,25,
    15,47,7,39,13,45,5,37,
    63,31,55,23,61,29,53,21
  ];

  function resolveCanvas(target) {
    if (target instanceof HTMLCanvasElement) return target;
    if (typeof target === 'string') return document.querySelector(target);
    return document.getElementById('silver-world-map');
  }

  function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message = gl.getShaderInfoLog(shader) || 'Unknown shader error';
      gl.deleteShader(shader);
      throw new Error(message);
    }

    return shader;
  }

  function createProgram(gl) {
    const vertexShader = compileShader(gl, gl.VERTEX_SHADER, VERT);
    const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, FRAG);
    const program = gl.createProgram();

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const message = gl.getProgramInfoLog(program) || 'Unknown program link error';
      gl.deleteProgram(program);
      throw new Error(message);
    }

    return program;
  }

  function buildMapCanvas() {
    const binary = atob(LAND_MASK);
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 256;

    const context = canvas.getContext('2d');
    const image = context.createImageData(512, 256);
    const data = image.data;

    for (let i = 0; i < 512 * 256; i += 1) {
      const bit = (binary.charCodeAt(i >> 3) >> (7 - (i & 7))) & 1;
      const value = bit ? 255 : 0;
      const offset = i * 4;

      data[offset] = value;
      data[offset + 1] = value;
      data[offset + 2] = value;
      data[offset + 3] = 255;
    }

    context.putImageData(image, 0, 0);
    return canvas;
  }

  function createMapTexture(gl) {
    const texture = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      buildMapCanvas()
    );
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return texture;
  }

  function createBayerTexture(gl) {
    const pixels = new Uint8Array(64 * 4);

    for (let i = 0; i < 64; i += 1) {
      const gray = Math.round(((BAYER_8X8[i] + 0.5) / 64) * 255);
      pixels[i * 4] = gray;
      pixels[i * 4 + 1] = gray;
      pixels[i * 4 + 2] = gray;
      pixels[i * 4 + 3] = 255;
    }

    const texture = gl.createTexture();
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      8,
      8,
      0,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      pixels
    );
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    return texture;
  }

  function mount(options = {}) {
    const canvas = resolveCanvas(options.canvas);

    if (!canvas) {
      throw new Error(
        'Canvas для карты не найден. Передайте options.canvas или добавьте #silver-world-map.'
      );
    }

    const gl = canvas.getContext('webgl', {
      alpha: true,
      antialias: false,
      depth: false,
      stencil: false,
      preserveDrawingBuffer: false
    });

    if (!gl) {
      throw new Error('WebGL не поддерживается этим браузером.');
    }

    const program = createProgram(gl);
    gl.useProgram(program);

    const positions = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positions);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]),
      gl.STATIC_DRAW
    );

    const positionLocation = gl.getAttribLocation(program, 'p');
    gl.enableVertexAttribArray(positionLocation);
    gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

    const uniforms = {
      resolution: gl.getUniformLocation(program, 'uRes'),
      time: gl.getUniformLocation(program, 'uTime'),
      map: gl.getUniformLocation(program, 'uMap'),
      bayer: gl.getUniformLocation(program, 'uBayer'),
      cell: gl.getUniformLocation(program, 'uCell')
    };

    const mapTexture = createMapTexture(gl);
    gl.uniform1i(uniforms.map, 0);

    const bayerTexture = createBayerTexture(gl);
    gl.uniform1i(uniforms.bayer, 1);

    const desktopCellSize = Number.isFinite(options.cellSize)
      ? options.cellSize
      : 8;

    const mobileCellSize = Number.isFinite(options.mobileCellSize)
      ? options.mobileCellSize
      : 6;

    const mobileBreakpoint = Number.isFinite(options.mobileBreakpoint)
      ? options.mobileBreakpoint
      : 700;

    let animationFrame = 0;
    let elapsed = 0;
    let lastTimestamp = 0;
    let destroyed = false;

    function resize() {
      if (destroyed) return;

      const rect = canvas.getBoundingClientRect();
      const width = Math.max(1, Math.round(rect.width || window.innerWidth));
      const height = Math.max(1, Math.round(rect.height || window.innerHeight));

      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      gl.viewport(0, 0, width, height);
      gl.useProgram(program);
      gl.uniform2f(uniforms.resolution, width, height);
      gl.uniform1f(
        uniforms.cell,
        width < mobileBreakpoint ? mobileCellSize : desktopCellSize
      );
    }

    function draw(timestamp) {
      if (destroyed) return;

      const delta = lastTimestamp
        ? Math.min((timestamp - lastTimestamp) / 1000, 0.05)
        : 0.016;

      lastTimestamp = timestamp;
      elapsed += delta;

      gl.useProgram(program);
      gl.uniform1f(uniforms.time, elapsed);
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      if (options.animate !== false) {
        animationFrame = requestAnimationFrame(draw);
      }
    }

    const resizeObserver =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(resize)
        : null;

    if (resizeObserver) resizeObserver.observe(canvas);
    window.addEventListener('resize', resize, { passive: true });

    resize();
    animationFrame = requestAnimationFrame(draw);

    return {
      canvas,
      gl,
      resize,

      setOpacity(value) {
        const opacity = Math.max(0, Math.min(1, Number(value)));
        canvas.style.opacity = String(opacity);
      },

      destroy() {
        if (destroyed) return;
        destroyed = true;

        cancelAnimationFrame(animationFrame);
        window.removeEventListener('resize', resize);
        if (resizeObserver) resizeObserver.disconnect();

        gl.deleteTexture(mapTexture);
        gl.deleteTexture(bayerTexture);
        gl.deleteBuffer(positions);
        gl.deleteProgram(program);
      }
    };
  }

  global.SilverDitherWorldMap = Object.freeze({ mount });
})(window);

    

        window.addEventListener('load', function () {
            try {
                window.oryxSilverWorldMap = SilverDitherWorldMap.mount({
                    canvas: '#dither-gl',
                    cellSize: 8,
                    mobileCellSize: 6,
                    mobileBreakpoint: 700
                });

                window.missionStageWorldMap = SilverDitherWorldMap.mount({
                    canvas: '#missionDitherGl',
                    cellSize: 8,
                    mobileCellSize: 6,
                    autoResize: true
                });

                window.missionBackdropWorldMap = SilverDitherWorldMap.mount({
                    canvas: '#missionBackdropGl',
                    cellSize: 8,
                    mobileCellSize: 6,
                    autoResize: true
                });

                window.mediaBackdropWorldMap = SilverDitherWorldMap.mount({
                    canvas: '#mediaBackgroundGl',
                    cellSize: 8,
                    mobileCellSize: 6,
                    autoResize: true
                });

                window.mediaSilverWorldMap = SilverDitherWorldMap.mount({
                    canvas: '#mediaDitherGl',
                    cellSize: 8,
                    mobileCellSize: 6,
                    mobileBreakpoint: 700
                });
            } catch (error) {
                console.warn('Silver world map initialization failed:', error);
            }
        });
    

(function () {
    function clean(root) {
        if (!root) return;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(node => {
            const parent = node.parentElement;
            if (!parent || ['SCRIPT','STYLE','CODE','PRE'].includes(parent.tagName)) return;
            const next = node.nodeValue.replace(/\[/g, '').replace(/\]/g, '');
            if (next !== node.nodeValue) node.nodeValue = next;
        });
    }
    clean(document.body);
    const observer = new MutationObserver(records => {
        records.forEach(record => {
            if (record.type === 'characterData') clean(record.target.parentElement);
            record.addedNodes.forEach(node => {
                if (node.nodeType === Node.TEXT_NODE) {
                    if (node.parentElement && !['SCRIPT','STYLE','CODE','PRE'].includes(node.parentElement.tagName)) {
                        node.nodeValue = node.nodeValue.replace(/\[/g, '').replace(/\]/g, '');
                    }
                } else if (node.nodeType === Node.ELEMENT_NODE) clean(node);
            });
        });
    });
    observer.observe(document.body, {subtree:true, childList:true, characterData:true});
})();

/* Body-content entrance fade, decoupled from the (now shared) heading
   transfer — unrelated to and unaffected by TransferCardController. */
function triggerBodyEnter(selector) {
  const el = document.querySelector(selector);
  if (!el) return;
  el.classList.remove('article-body-enter');
  void el.offsetWidth;
  el.classList.add('article-body-enter');
}

/* ============================================================================
   0A — SYSTEM ARCHITECTURE heading: proportional shift and a heavier weight,
   both recomputed from the live layout rather than pinned to one resolution.
   ============================================================================ */
(function () {
  function applyHeadingCorrection() {
    const header = document.querySelector('header');
    const shell = document.querySelector('.architecture-shell');
    if (!header || !shell) return;
    const label = shell.querySelector('.media-shell-header .technical-label');
    if (!label) return;

    label.style.transform = '';
    const gap = shell.getBoundingClientRect().top - header.getBoundingClientRect().bottom;
    if (gap > 0) label.style.transform = 'translateY(' + (gap * 0.05).toFixed(2) + 'px)';

    if (!label.dataset.baseWeight) {
      label.style.removeProperty('font-weight');
      label.dataset.baseWeight = getComputedStyle(label).fontWeight || '600';
    }
    const base = parseInt(label.dataset.baseWeight, 10) || 600;
    const stepped = Math.min(900, Math.round(base * 1.1 / 50) * 50);
    label.style.setProperty('font-weight', String(stepped), 'important');
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyHeadingCorrection);
  } else {
    applyHeadingCorrection();
  }
  window.addEventListener('resize', applyHeadingCorrection);
  window.addEventListener('load', applyHeadingCorrection);
})();

/* ============================================================================
   SOCIAL FEED — normalized SocialPost records behind a provider boundary.
   Swapping the provider for a CMS or server importer needs no UI change.
   ============================================================================ */
const localSocialPosts = [
  {
    id: 'linkedin-xra-2e5-hardware',
    platform: 'linkedin',
    publishedAt: '2026-03-23',
    text: "XRA-2E5: Aspire Space's orbital-class second-stage aerospike hardware milestone developed under the propulsion programme with LEAP 71.",
    permalink: 'https://www.linkedin.com/posts/aspirespaceuae_leap-71-%D1%85-aspire-space-200-kn-aerospike-activity-7441823279562035200-RLeS',
    sourceLabel: 'Aspire Space'
  },
  {
    id: 'linkedin-oryx-performance-update',
    platform: 'linkedin',
    publishedAt: '2026-05-11',
    text: 'Oryx structural rework update: R1v5, D3, revised payload capability, gear ratio 26 and the path toward the full-reuse cost target.',
    permalink: 'https://www.linkedin.com/posts/aspirespaceuae_spacetech-computationalengineering-activity-7459624369955164160-_fFn',
    sourceLabel: 'Aspire Space',
    media: [{ type: 'image', url: 'assets/images/R1V5.png', alt: 'R1v5 booster' }]
  },
  {
    id: 'linkedin-hotfire-and-oryx-press',
    platform: 'linkedin',
    publishedAt: '2026-05-13',
    text: 'Questions from Make it in the Emirates on the $200/kg target, aerospikes, the XRA-2E5 hot-fire campaign and the Oryx flight roadmap.',
    permalink: 'https://www.linkedin.com/posts/aspirespaceuae_what-does-200kg-to-orbit-actually-mean-activity-7460262812804792320-dy35',
    sourceLabel: 'Aspire Space'
  },
  {
    id: 'linkedin-oryx-introduction',
    platform: 'linkedin',
    publishedAt: '2025-11-17',
    text: 'Aspire Space introduces Oryx, a fully reusable two-stage space transportation system built around rapid turnaround and repeated flight.',
    permalink: 'https://www.linkedin.com/posts/aspirespaceuae_rockets-arent-enough-anymore-the-new-space-activity-7396122557357232129-1Ou0',
    sourceLabel: 'Aspire Space',
    media: [{ type: 'image', url: 'assets/images/oryx-orbit-2.png', alt: 'Oryx in orbit' }]
  }
];

async function getSocialPosts() {
  return localSocialPosts;
}

(function () {
  const VISIBLE_LIMIT = 8;
  const PLATFORM_LABEL = { linkedin: 'LinkedIn', x: 'X', instagram: 'Instagram' };

  function formatDate(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
  }

  function renderCard(post) {
    const card = document.createElement('a');
    card.className = 'social-card';
    card.href = post.permalink;
    card.target = '_blank';
    card.rel = 'noopener noreferrer';

    const image = (post.media || []).find(function (m) { return m.type === 'image'; });
    if (image) {
      const wrap = document.createElement('div');
      wrap.className = 'social-card-media';
      const img = document.createElement('img');
      img.src = image.url;
      img.alt = image.alt || '';
      img.loading = 'lazy';
      wrap.appendChild(img);
      card.appendChild(wrap);
    }

    const body = document.createElement('div');
    body.className = 'social-card-body';

    const meta = document.createElement('div');
    meta.className = 'social-card-meta';
    const platform = document.createElement('span');
    platform.className = 'social-card-platform';
    platform.textContent = PLATFORM_LABEL[post.platform] || post.platform;
    const date = document.createElement('span');
    date.textContent = formatDate(post.publishedAt);
    meta.appendChild(platform);
    meta.appendChild(date);

    const text = document.createElement('p');
    text.className = 'social-card-text';
    text.textContent = post.text;

    const link = document.createElement('span');
    link.className = 'social-card-link';
    link.textContent = 'Open post ↗';

    body.appendChild(meta);
    body.appendChild(text);
    body.appendChild(link);
    card.appendChild(body);
    return card;
  }

  function renderFeed(grid, posts) {
    grid.textContent = '';
    if (!posts.length) {
      const empty = document.createElement('div');
      empty.className = 'social-feed-empty';
      empty.textContent = 'No public posts yet.';
      grid.appendChild(empty);
      return;
    }
    posts
      .slice()
      .sort(function (a, b) {
        if (!!b.featured !== !!a.featured) return (b.featured ? 1 : 0) - (a.featured ? 1 : 0);
        return new Date(b.publishedAt) - new Date(a.publishedAt);
      })
      .slice(0, VISIBLE_LIMIT)
      .forEach(function (post) { grid.appendChild(renderCard(post)); });
  }

  async function init() {
    const grid = document.getElementById('socialFeedGrid');
    if (!grid) return;
    renderFeed(grid, await getSocialPosts());
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
