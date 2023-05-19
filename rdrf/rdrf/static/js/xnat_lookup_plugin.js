(function($) {

  $.fn.xnat_lookup = function(options) {

    const settings = $.extend({
      widget_id: '',
      initial_project_id: '',
      initial_subject_id: '',
      base_lookup_url: '/xnat_scans',
      base_xnat_url: ''
    }, options);

    const $widget = $(this);

    const $xnatProjectId = $(`#id_${settings.widget_id}_project_id`);
    const $xnatSubjectId = $(`#id_${settings.widget_id}_subject_id`);
    const $xnatField = $(`#id_${settings.widget_id}`);
    const $lookupButton = $widget.find('[data-xnat="trigger_lookup"]');

    const $loadingMessage =  $widget.find('[data-xnat="loading"]');
    const $resultsContainer = $widget.find('[data-xnat="result"]');
    const $resultsTable = $widget.find('[data-xnat="result_table"]');
    const $resultsError = $widget.find('[data-xnat="result_error"]');

    function toggleDisplay(elem, show) {
      elem.toggleClass('d-none', !show);
    }

    function displayError(error_text) {
      $resultsTable.find('tbody').empty();
      $resultsError.text(error_text);
      toggleDisplay($resultsError, true);
      toggleDisplay($resultsTable, false);
    }

    async function loadExperiments(project_id, subject_id) {
      toggleDisplay($loadingMessage, true);
      toggleDisplay($resultsContainer, false);
      toggleDisplay($resultsError, false);

      const url = `${settings.base_lookup_url}/${project_id}/${subject_id}`;

      $.ajax({
        url: url,
        success: function(data) {
          $resultsTable.find('tbody').empty();
          $resultsTable.find('caption').text(gettext('Results for') + ` ${project_id}, ${subject_id}`);
          for (const experiment of data.experiments) {
            for (const scan of experiment.scans) {
              $resultsTable.find('tbody')
                .append($('<tr>')
                  .append($('<td>').text(experiment.date))
                  .append($('<td>').text(`${experiment.label} (${experiment.id})`))
                  .append($('<td>').append($('<a>')
                    .attr('href', settings.base_xnat_url + scan.URI)
                    .attr('target', '_blank')
                    .attr('rel', 'noopener noreferrer')
                    .text(`${scan.id} (${scan.type})`)
                  ))
                  .append($('<td>').text(scan.series_description))
                );
            }
          }
          toggleDisplay($resultsTable, true);
        },
        statusCode: {
          403: function() {
            displayError(gettext("You do not have access to XNAT."))
          }
        },
        error: function($xhr) {
          if ($xhr["responseJSON"] && $xhr["responseJSON"]["message"]) {
            displayError($xhr.responseJSON.message);
          } else {
            displayError(gettext("Could not load results from XNAT."));
          }
        },
        complete: function() {
          toggleDisplay($loadingMessage, false);
          toggleDisplay($resultsContainer, true);
        }
      });

    }

    const methods = {
      setInitialValue: function() {
        $xnatProjectId.val(settings.initial_project_id);
        $xnatSubjectId.val(settings.initial_subject_id);
      },
      initEventHandlers: function() {
        [$xnatProjectId, $xnatSubjectId].forEach(function() {
          $(this).on('change', function() {
            $xnatField.val($xnatProjectId.val() + ';' + $xnatSubjectId.val());
          });
        })

        $lookupButton.on('click', async function () {
          await loadExperiments($xnatProjectId.val(), $xnatSubjectId.val());
        });
      }
    }

    // setup
    methods.setInitialValue();
    methods.initEventHandlers();
  }

}(jQuery));

