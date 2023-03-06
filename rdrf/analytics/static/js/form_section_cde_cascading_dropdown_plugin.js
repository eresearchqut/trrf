(function($) {
  $.fn.cascading_cde_selector = function(options) {

    const $element = this;

    const settings = $.extend({
      $registry: null,
    }, options);


    function update_dropdown($select, data, value, text) {
        $select.empty();
        $select.append($('<option />').attr('value', '').text(''));
        for (const entry of data) {
          let option_text;
          if (typeof text === 'function') {
            option_text = text(entry);
          } else {
            option_text = entry[text];
          }
          $select.append($('<option />').attr('value', entry[value]).text(option_text));
        }
      }


      const update_registries = function($registry) {
        $.ajax("/api/v1/registries/", {
          success: function(data) {
            update_dropdown($registry, data, 'id', 'name');
          }
        });
      }

      const update_forms = function($form, registry_id) {
        const option_text = function(entry) {
          return `${entry.nice_name} (${entry.name})`;
        }
        $.ajax(`/api/v1/registries/${registry_id}/forms/`, {
          success: function(data) {
            update_dropdown($form, data, 'id', option_text);
          }
        });
      }

      const update_sections = function($section, form_id) {
        const option_text = function(entry) {
          let display_name = entry.display_name.trim();
          if (!display_name) {
            return entry.code
          }
          return display_name;
        }
        $.ajax(`/api/v1/forms/${form_id}/sections/`, {
          success: function(data) {
            update_dropdown($section, data, 'id', option_text);
          }
        });
      }

      const update_cdes = function ($cde, section_id) {
        $.ajax(`/api/v1/sections/${section_id}/cdes/`, {
          success: function(data) {
            update_dropdown($cde, data, 'code', 'name');
          }
        });
      }

      const init_form_elements = function() {

        const $form = $element.find('[data-cde-widget="form"]');
        console.log($form.attr('id'));
        const $section = $element.find('[data-cde-widget="section"]');
        const $cde = $element.find('[data-cde-widget="cde"]');

        const change_events = [
          {trigger: settings.$registry, fn: update_forms, target: $form},
          {trigger: $form, fn: update_sections, target: $section},
          {trigger: $section, fn: update_cdes, target: $cde},
        ]

        for (const event of change_events) {
          event.trigger.on('change', function() {
            const value = $(this).val();
            event.fn(event.target, value)
          });
        }

        // update_registries($registry);
      }

    init_form_elements();

    return {
      update_registries: function () {
        console.log('registry update')
        console.log(settings.$registry);
        update_registries(settings.$registry);
      }
    }
  }
}(jQuery));