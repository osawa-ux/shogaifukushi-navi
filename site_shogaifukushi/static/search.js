
(function() {
    var input = document.getElementById('searchInput');
    var cards = document.querySelectorAll('.clinic-card');
    var filterBar = document.getElementById('filterBar');
    var filterReset = document.getElementById('filterReset');
    var sortSelect = document.getElementById('sortSelect');
    if (!cards.length) return;

    function applyFilters() {
        var q = input ? input.value.trim().toLowerCase() : '';
        var filters = {};
        if (filterBar) {
            filterBar.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
                if (cb.checked) filters[cb.dataset.filter] = true;
            });
        }
        var hasFilters = Object.keys(filters).length > 0;
        if (filterReset) filterReset.style.display = hasFilters ? '' : 'none';

        var shown = 0;
        cards.forEach(function(card) {
            var text = card.textContent.toLowerCase();
            var textMatch = !q || text.includes(q);
            var filterMatch = true;
            for (var key in filters) {
                if (card.dataset[key] !== 'true') { filterMatch = false; break; }
            }
            if (textMatch && filterMatch) {
                card.style.display = '';
                shown++;
            } else {
                card.style.display = 'none';
            }
        });
        var counter = document.getElementById('searchCount');
        if (counter) counter.textContent = (q || hasFilters) ? shown + '件表示中' : '';
        var noResult = document.getElementById('noResultMsg');
        if (shown === 0 && (q || hasFilters)) {
            if (!noResult) {
                noResult = document.createElement('p');
                noResult.id = 'noResultMsg';
                noResult.style.cssText = 'text-align:center;color:#888;padding:20px;';
                noResult.textContent = '条件に一致する事業所が見つかりませんでした';
                var list = document.querySelector('.clinic-list');
                if (list) list.parentNode.insertBefore(noResult, list.nextSibling);
            }
            noResult.style.display = '';
        } else if (noResult) {
            noResult.style.display = 'none';
        }
    }

    if (input) input.addEventListener('input', applyFilters);
    if (filterBar) filterBar.addEventListener('change', applyFilters);
    if (filterReset) filterReset.addEventListener('click', function() {
        filterBar.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = false; });
        applyFilters();
    });

    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            var list = document.querySelector('.clinic-list');
            if (!list) return;
            var items = Array.from(list.querySelectorAll('.clinic-card'));
            if (this.value === 'name') {
                items.sort(function(a, b) {
                    var na = a.querySelector('.clinic-name') ? a.querySelector('.clinic-name').textContent : '';
                    var nb = b.querySelector('.clinic-name') ? b.querySelector('.clinic-name').textContent : '';
                    return na.localeCompare(nb, 'ja');
                });
            } else {
                items.sort(function(a, b) {
                    return parseInt(a.dataset.order || '0') - parseInt(b.dataset.order || '0');
                });
            }
            items.forEach(function(item) { list.appendChild(item); });
        });
    }
})();
