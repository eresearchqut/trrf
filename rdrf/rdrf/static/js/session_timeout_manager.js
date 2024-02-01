function ModalSessionNotifier(options) {

    const settings = $.extend({
        $modal: undefined,
        sessionExpiryTimeoutSelector: undefined
    }, options);

    const SessionState = {
        Expiring: "expiring",
        Expired: "expired"
    }

    const CountdownIncrements = {
        EVERY_HALF_MINUTE: 30,
        EVERY_SECOND: 1
    }

    const $sessionTimeoutModal = settings.$modal;
    const $sessionExpiredComponents = $(`[data-session-state="${SessionState.Expired}"]`);
    const $sessionExpiringComponents = $(`[data-session-state="${SessionState.Expiring}"]`);
    const sessionTimeoutModal = new bootstrap.Modal($sessionTimeoutModal, {backdrop: "static"});

    let sessionExpiryTimestamp;
    let nextCountdownUpdateInSeconds = CountdownIncrements.EVERY_HALF_MINUTE;
    let countdownInterval;

    document.addEventListener("visibilitychange", function() {
        if (!document.hidden && countdownInterval && sessionExpiryTimestamp) {
            // update the countdown timer when the user comes back to this site from elsewhere.
            countdownTimer();
        }
    });

    function updateSessionTimeoutMessage(secondsLeft) {
        const ONE_MINUTE_IN_SECONDS = 60;
        let timeoutText = "";

        if (secondsLeft >= ONE_MINUTE_IN_SECONDS) {
            const minutesLeft = Math.round(secondsLeft / ONE_MINUTE_IN_SECONDS);
            timeoutText = interpolate(ngettext("%s minute", "%s minutes", minutesLeft), [minutesLeft]);
        } else {
            const roundedSecondsLeft = Math.round(secondsLeft);
            timeoutText = interpolate(ngettext("%s second", "%s seconds", roundedSecondsLeft), [roundedSecondsLeft]);
        }

        $sessionTimeoutModal.find(settings.sessionExpiryTimeoutSelector).text(timeoutText);
    }

    function countdownTimer() {
        const now = new Date()
        const secondsLeftInSession = (sessionExpiryTimestamp.getTime() - now.getTime()) / 1000;
        if (secondsLeftInSession > 0) {
            updateSessionTimeoutMessage(secondsLeftInSession);
            if (nextCountdownUpdateInSeconds === CountdownIncrements.EVERY_HALF_MINUTE && secondsLeftInSession < 60 ) {
                nextCountdownUpdateInSeconds = CountdownIncrements.EVERY_SECOND;
                clearInterval(countdownInterval)
                countdownInterval = setInterval(countdownTimer, nextCountdownUpdateInSeconds * 1000);
            }
        } else {
            clearNotifier();
            displayComponents(SessionState.Expired)
        }
    }

    function displayComponents(sessionState) {
        switch (sessionState) {
            case SessionState.Expiring: {
                $sessionExpiredComponents.addClass("d-none");
                $sessionExpiringComponents.removeClass("d-none");
                break;
            }
            case SessionState.Expired: {
                $sessionExpiredComponents.removeClass("d-none");
                $sessionExpiringComponents.addClass("d-none");
                $('.modal-backdrop').css("opacity", ".9");
                break;
            }
        }
    }

    function clearNotifier() {
        if (countdownInterval) clearInterval(countdownInterval);
        nextCountdownUpdateInSeconds = CountdownIncrements.EVERY_HALF_MINUTE;
        sessionExpiryTimestamp = undefined;
    }

    function show(_sessionExpiryTimestamp) {
        sessionExpiryTimestamp = _sessionExpiryTimestamp;
        countdownInterval = setInterval(countdownTimer, nextCountdownUpdateInSeconds * 1000);
        countdownTimer();
        displayComponents(SessionState.Expiring);
        sessionTimeoutModal.show();
    }

    function showExpired() {
        displayComponents(SessionState.Expired);
        sessionTimeoutModal.show()
    }

    return {
        clearNotifier,
        show,
        showExpired
    }
}

function SessionManager(sessionNotifier, options) {

    const settings = $.extend({
      session: {
          maxAge: undefined,
          warningLeadTime: undefined,
          refreshLeadTime: undefined
      },
      urls: {
          sessionRefresh: undefined,
          login: undefined,
          logout: undefined
      }
    }, options);

    const maxSessionAge = settings.session.maxAge;
    const sessionWarningLeadTime = settings.session.warningLeadTime;
    const sessionRefreshLeadTime = settings.session.refreshLeadTime;
    const secondsUntilNextSessionRefresh = maxSessionAge - sessionRefreshLeadTime;
    const secondsUntilExpiryWarning = maxSessionAge - sessionWarningLeadTime;
    let sessionRefreshInterval;
    let warningTimeout;
    let restartCount = 0;

    function keepAlive(forcedRefresh = false) {
        const data = {};
        if (forcedRefresh) data['forced_refresh'] = true;
        return $.ajax({
            url: settings.urls.sessionRefresh,
            type: "get",
            data
        })
            .fail(function() { alert(gettext("Error while refreshing session. Please check your connection"));
        });
    }

    function sessionRefresh(forcedRefresh = false) {
        keepAlive(forcedRefresh).then(function ( data, status, jqXHR ) {
            if (forcedRefresh && data.success === undefined) {
                sessionNotifier.showExpired();
            } else {
                if (data && !data.success) {
                    const expiryTimestamp = new Date();
                    expiryTimestamp.setSeconds(expiryTimestamp.getSeconds() + maxSessionAge);
                    clearInterval(sessionRefreshInterval);
                    warningTimeout = setTimeout(() => { sessionNotifier.show(expiryTimestamp)}, secondsUntilExpiryWarning * 1000);
                }
            }
        });
    }

    function restart() {
        if (warningTimeout) clearTimeout(warningTimeout);
        sessionNotifier.clearNotifier();

        if (restartCount > 0) {
            sessionRefresh(true);
        }
        restartCount += 1;

        clearInterval(sessionRefreshInterval);
        sessionRefreshInterval = setInterval(sessionRefresh, secondsUntilNextSessionRefresh * 1000);
    }

    function logout() {
        window.location.href = settings.urls.logout;
    }

    function goToLoginPage() {
        window.location.href = settings.urls.login;
    }

    // initialise session manager
    restart();

    return {
        restart,
        logout,
        goToLoginPage
    }

}