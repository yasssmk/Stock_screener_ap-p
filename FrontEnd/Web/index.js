$(document).ready(function() {
    $('.btn-outline-light').on('click', function() {
        var $this = $(this);

        $this.addClass('button-pressed');

        // Remove the class after the animation completes
        setTimeout(function() {
            $this.removeClass('button-pressed');
        }, 400); // The duration should match the CSS animation
    });
});

