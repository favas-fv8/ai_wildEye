/* Ai-WildEye Main JavaScript */
document.addEventListener('DOMContentLoaded', function() {
    // Mobile navigation toggle
    const toggler = document.querySelector('.navbar-toggler');
    const navLinks = document.querySelector('.nav-links');
    
    if (toggler && navLinks) {
        toggler.addEventListener('click', function() {
            navLinks.classList.toggle('show');
            this.setAttribute('aria-expanded', navLinks.classList.contains('show'));
        });

        // Close on outside click
        document.addEventListener('click', function(e) {
            if (!toggler.contains(e.target) && !navLinks.contains(e.target)) {
                navLinks.classList.remove('show');
                toggler.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // Dropdown keyboard accessibility
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(function(dropdown) {
        const trigger = dropdown.querySelector('.nav-link');
        const menu = dropdown.querySelector('.dropdown-menu');
        
        if (trigger && menu) {
            trigger.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    menu.classList.toggle('show');
                }
                if (e.key === 'Escape') {
                    menu.classList.remove('show');
                }
            });

            // Close on outside click
            document.addEventListener('click', function(e) {
                if (!dropdown.contains(e.target)) {
                    menu.classList.remove('show');
                }
            });
        }
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            const result = alert.closest('.analysis-result');
            if (result) {
                result.style.opacity = '0';
                result.style.transition = 'opacity .3s ease';
            }
            setTimeout(function() {
                (result || alert).remove();
            }, 300);
        }, 5000);
    });

    // Alert close button
    document.querySelectorAll('.alert-close').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const alert = this.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                const result = alert.closest('.analysis-result');
                if (result) {
                    result.style.opacity = '0';
                    result.style.transition = 'opacity .3s ease';
                }
                setTimeout(function() {
                    (result || alert).remove();
                }, 300);
            }
        });
    });

    // Form loading state
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            const btn = this.querySelector('button[type="submit"]');
            if (btn && !btn.classList.contains('no-loading')) {
                btn.disabled = true;
                btn.dataset.originalText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner spinner-sm"></span> Processing...';
            }
        });
    });

    // Confirm delete actions
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Are you sure?')) {
                e.preventDefault();
            }
        });
    });

    // File input label update
    document.querySelectorAll('.form-control-file').forEach(function(input) {
        input.addEventListener('change', function() {
            const label = this.previousElementSibling;
            if (label && label.classList.contains('form-label')) {
                const fileName = this.files[0] ? this.files[0].name : 'Choose file';
                label.textContent = fileName;
            }
        });
    });
});

/* Utility: Fetch with CSRF token */
function csrfFetch(url, options = {}) {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!csrftoken) {
        console.error('CSRF token not found');
        return Promise.reject('CSRF token not found');
    }

    const defaults = {
        headers: {
            'X-CSRFToken': csrftoken.value,
            'X-Requested-With': 'XMLHttpRequest',
        }
    };

    return fetch(url, Object.assign({}, defaults, options));
}