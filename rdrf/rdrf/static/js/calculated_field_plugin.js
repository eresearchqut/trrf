(function($) {
    $.fn.add_calculation = function(options) {
        var settings = $.extend({
            // These are the defaults.
            calculation: function(context) { context.result = "???"; },
            subjects: '', // E.g. "CDE01,CDE02" comma separated list of inputs to the calculation
            prefix: '',//  formcode^^sectioncode^^
            target: "value",
            observer: '',  // the cde code of the output e,g, CDE03
            // Stuff below added to allow calculations to retrieve remote model properties
            // injected_model will always be Patient for now
            injected_model: "",  // e.g. Patient  ( model class name)
            injected_model_id: null,  // the id of the injected model instance to retrieve
            api_url: ""  //the url to request model data on eg cde_query

        }, options);



        // locate the codes anywhere on the page ( we assume only one occurrence of given cde for now
        function locate_code(code, filterChecked=false) {
            const id = $('[id*=' + code + ']').attr("id");
            const idSelector = `#${id}`;

            if ($(idSelector).is(":input")) {
                return idSelector
            }

            const name = $("input[name*='" + code + "']").attr("name");
            const nameSelector = "input[name='" + name + "']";

            if ($(nameSelector).is(":radio")) {
                return filterChecked ? `${nameSelector}:checked` : nameSelector;
            }

        }

        var subject_codes_string;
        if (settings.subjects) {
            subject_codes_string = _.map(settings.subjects.split(","), function (code) {
                return locate_code(code);
            }).join();
        }

        function get_object(model, model_id) {
            var d = $.Deferred();
             if (model_id == -1) {
                 d.resolve([]);
                 return;
            }

            $.get(settings.api_url)
                .done(function(object) {
                    if (object.success && object.patient) {
                        d.resolve(object.patient);
                    } else {
                        if (object.error) {
                            d.reject(object.error);
                        }
                        d.reject('Unexpected response from api');
                    }

                })
                .fail(d.reject);

            return d.promise();
        }

        var update_function = function() {
            var context = {};

            if (settings.subjects) {
                var subject_codes = settings.subjects.split(",");

                for (var i = 0; i < subject_codes.length; i++) {
                    // Note how we use the prefix to map from the page to the context variable names
                    // and reverse map to update the output
                    var subject_code_selector = locate_code(subject_codes[i], true);
                    context[subject_codes[i]] = $(subject_code_selector).val();
                }
            }

            var model_promise = get_object(settings.injected_model.toLowerCase(),
                                           settings.injected_model_id);

            return $.when(model_promise).done(function(injected_models) {
               try {
                   settings.calculation.apply(null, [context].concat(injected_models));
               }
               catch (err) {
                   console.error("CDE calculation error", err);
                   context.result = "ERROR";
               }
               $("#id_" + settings.prefix + settings.observer).val(context.result);
               $("#id_" + settings.prefix + settings.observer).trigger("rdrf_calculation_performed");

               // Apply conditional rendering, as the change of calculation value may trigger a form state change
               // If the visibility_handler function is not defined, it has likely been disabled.
               if (typeof visibility_handler === 'function') {
                   render_changes(visibility_handler());
               }
            })
            .fail(function(e) {
                console.error('CDE calculation error', e);
            });
        };

        $(subject_codes_string).on("input change", update_function);
        $(subject_codes_string).on("rdrf_calculation_performed", update_function);

        try {
            // call on initial page load
            update_function(); //call it to ensure if calculation changes on server
                               // we are always in sync(RDR-426 )
        }
        catch (err) {
            alert(err);
        }
    };

}(jQuery));
