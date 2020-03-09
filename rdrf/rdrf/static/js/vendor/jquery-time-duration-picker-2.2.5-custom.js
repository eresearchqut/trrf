/*!
 * jquery-time-duration-picker
 *
 * https://github.com/digaev/jquery-time-duration-picker
 *
 * Copyright (c) 2015-2019 Nikolay Digaev
 * Released under the MIT license
 */

( function( $ ) {
  var defaults = {
    lang: "en_US",
    css: {
      position: "absolute"
    },
    years: {active:true, min: -1, max: -1},
    weeks: {active:false, min: -1, max: - 1},
    months: {active:true, min: -1, max: -1},
    days: {active: true, min: -1, max: -1},
    hours: {active:true, min: -1, max: -1},
    minutes: {active:true, min: -1, max: -1},
    seconds: {active:false, min: -1, max: -1}
  };
  $.timeDurationPicker = {
    defaults: function( options ) {
      var opts = $.extend( true, {}, defaults, options );
      if ( options ) {
        defaults = opts;
      } else {
        return opts;
      }
    },
    langs: {
      en_US: {
        years: "Years",
        months: "Months",
        weeks: "Weeks",
        days: "Days",
        hours: "Hours",
        minutes: "Minutes",
        seconds: "Seconds",
        and: "and",
        button_ok: "OK",
        units: {
          year: {
            one: "year",
            other: "years"
          },
          month: {
            one: "month",
            other: "months"
          },
          week: {
            one: "week",
            other: "weeks"
          },
          day: {
            one: "day",
            other: "days"
          },
          hour: {
            one: "hour",
            other: "hours"
          },
          minute: {
            one: "minute",
            other: "minutes"
          },
          second: {
            one: "second",
            other: "seconds"
          }
        }
      }
    },
    i18n: {
      t: function( lang, key, count ) {
        if ( count ) {
          key += "." + this.pluralRules[ lang ]( count );
        }

        var keys = key.split( "." );
        var text = $.timeDurationPicker.langs[ lang ][ keys[ 0 ] ];
        for ( var i = 1; i < keys.length; ++i ) {
          text = text[ keys[ i ] ];
        }
        if ( count ) {
          text = count + " " + text;
        }
        return text;
      },

      // http://unicode.org/repos/cldr-tmp/trunk/diff/supplemental/language_plural_rules.html
      pluralRules: {
        en_US: function( count ) {
          return parseInt( count ) === 1 ? "one" : "other";
        }
      }
    }
  };
  $.timeDurationPicker.defaults();
} )( jQuery );

( function( $ ) {
  var instances = [];

  $( document ).focusin( function( e ) {
    for ( var i = 0, c = instances.length; i < c; ++i ) {
      var inst = instances[ i ];
      for ( var j = 0, l = inst.element.length; j < l; ++j ) {
        if ( inst.element[ j ] === e.target ) {
          var offset = $( e.target ).offset();
          offset.top += $( e.target ).outerHeight();
          inst._content.div.css( offset ).fadeIn();
          inst._restore();
        }
      }
    }
  } ).focusout( function() {

    // FIXME: how to correctly detect that the element has lost focus?
    setTimeout( function() {
      var el = document.activeElement;
      if ( $( el ).parents( ".time-duration-picker-content" ).length === 0 ) {
        for ( var i = 0, c = instances.length; i < c; ++i ) {
          var hide = true;
          var inst = instances[ i ];
          for ( var j = 0, l = inst.element.length; j < l; ++j ) {
            if ( inst.element[ j ] === el ) {
              hide = false;
              break;
            }
          }
          if ( hide ) {
            inst._content.div.fadeOut();
          }
        }
      }
    }, 10 );
  } );

  var YEAR = 12 * 30 * 24 * 60 * 60;
  var MONTH = 30 * 24 * 60 * 60;
  var WEEK = 7 * 24 * 60 * 60;
  var DAY = 24 * 60 * 60;
  var HOUR = 60 * 60;
  var MINUTE = 60;

  $.widget( "custom.timeDurationPicker", {
    options: {
    },
    _create: function() {
      var self = this;

      this.units = ["years", "months", "weeks", "days", "hours", "minutes", "seconds"];
      this.options = $.extend(
        true, {}, $.timeDurationPicker.defaults(), this.options
      );

      this._content = {};
      this._content.div = $( "<div />" );
      this._content.div.addClass( "ui-widget ui-widget-content ui-helper-clearfix ui-corner-all" );
      this._content.div.addClass( "time-duration-picker-content" );
      this._content.div.css( $.extend( {
          display: "none",
          "z-index": 401
      }, this.options.css ) );
      this._content.div.appendTo( document.body );

      this._content.table = $(
        "<table style='width: 100%;'><tbody /></table>"
      ).appendTo( this._content.div );
      this._content.tableBody = $( "tbody", this._content.table );

      this._initUnits();

      instances.push( this );
    },
    _on_change: function(unit) {
      this._save();
      if ( this.options.onSelect ) {
        this.options.onSelect.call(
          this, this.element, this.getSeconds(), this.getDuration(), this.translate()
        );
      }
    },

    _destroy: function() {
      var i = instances.indexOf( this );

      if ( i > -1 ) {
        instances.splice( i, 1 );
      }

      this._content.div.remove();
    },
    _initUnits: function() {
      for ( var i = 0; i < this.units.length; ++i ) {
        var u = this.units[ i ];
        if ( this.options[ u ] && this.options[u].active) {
          var min_val = this.options[u].min == -1 ? 0: this.options[u].min;
          var max_val = this.options[u].max == -1 ? 0: this.options[u].max;
          if (max_val == 0 && u == "weeks") {
            max_val = 53;
          }
          this._content[ u ] = this._createNumberInput(u, 0, min_val, max_val);
          this._appendRow( this._t( u ), this._content[ u ] );
        }
      }

      if ( this.options.defaultValue ) {
        var value;

        if ( typeof this.options.defaultValue === "function" ) {
          value = this.options.defaultValue.call( this );
        } else {
          value = this.options.defaultValue;
        }

        switch ( typeof value ) {
        case "number":
          this.setSeconds( value );
          break;
        case "string":
          this.setDuration( value );
          break;
        default:
          throw new Error( "Unexpected default value type" );
        }

        this._save();
        this.element.val( this.translate() );
      }
    },
    _createNumberInput: function(unit, value, min, max) {
      var input = $( "<input type='number' />" );

      value = parseInt( value, 10 );
      min = parseInt( min, 10 );
      max = parseInt( max, 10 );

      input.css( {
        display: "block",
        width: "4.5em"
      } );

      if ( !isNaN( value ) ) {
        input.attr( "value", value );
      }

      if ( !isNaN( min ) ) {
        input.attr( "min", min );
      }

      if ( !isNaN( max ) ) {
        input.attr( "max", max );
      }

      var self = this;
      var u = unit;
      input.change(function() {
        self._on_change(u);
      });

      return input;
    },
    _appendRow: function( text, el ) {
      var row = $( "<tr />" ).appendTo( this._content.tableBody );
      $( "<td />" ).css( {
        width: "50%",
        padding: ".5em 1em",
        "text-align": "right",
        "vertical-align": "middle"
      } ).append( $( "<strong />" )
        .text( text ) )
        .appendTo( row );
      $( "<td />" ).css( {
        width: "50%",
        padding: ".5em 1em",
        "text-align": "right",
        "vertical-align": "middle"
      } ).append( el )
        .appendTo( row );
    },
    _t: function( key, count ) {
      return $.timeDurationPicker.i18n.t( this.options.lang, key, count );
    },

    _save: function() {
      this._duration = {};

      if ( this.options.years && this.options.years.active ) {
        this._duration.years = this.years();
      }

      if ( this.options.months && this.options.months.active ) {
        this._duration.months = this.months();
      }

      if (this.options.weeks && this.options.weeks.active) {
        this._duration.weeks = this.weeks();
      }

      if ( this.options.days && this.options.days.active) {
        this._duration.days = this.days();
      }

      if ( this.options.hours && this.options.hours.active ) {
        this._duration.hours = this.hours();
      }

      if ( this.options.minutes && this.options.minutes.active ) {
        this._duration.minutes = this.minutes();
      }

      if ( this.options.seconds && this.options.seconds.active ) {
        this._duration.seconds = this.seconds();
      }
    },
    _restore: function() {
      if ( !this._duration ) {
        this._duration = {};
      }

      if ( this.options.years && this.options.years.active ) {
         this.years( this._duration.years || 0 );
      }

      if ( this.options.months && this.options.months.active ) {
        this.months( this._duration.months || 0 );
      }

      if ( this.options.weeks && this.options.weeks.active ) {
        this.weeks( this._duration.weeks || 0 );
      }

      if ( this.options.days && this.options.days.active) {
        this.days( this._duration.days || 0 );
      }

      if ( this.options.hours && this.options.hours.active) {
        this.hours( this._duration.hours || 0 );
      }

      if ( this.options.minutes && this.options.minutes.active) {
        this.minutes( this._duration.minutes || 0 );
      }

      if ( this.options.seconds && this.options.seconds.active) {
        this.seconds( this._duration.seconds || 0 );
      }
    },
    seconds: function( val ) {
      if ( !isNaN( val = parseInt( val, 10 ) ) ) {
        this._content.seconds.val( val );
      } else {
        return parseInt( this._content.seconds.val(), 10 );
      }
    },
    minutes: function( val ) {
      if ( !isNaN( val = parseInt( val, 10 ) ) ) {
        this._content.minutes.val( val );
      } else {
        return parseInt( this._content.minutes.val(), 10 );
      }
    },
    hours: function( val ) {
      if ( !isNaN( val = parseInt( val, 10 ) ) ) {
        this._content.hours.val( val );
      } else {
        return parseInt( this._content.hours.val(), 10 );
      }
    },
    days: function( val ) {
      if ( !isNaN( val = parseInt( val, 10 ) ) ) {
        this._content.days.val( val );
      } else {
        return parseInt( this._content.days.val(), 10 );
      }
    },
    weeks: function( val ) {
      if ( !isNaN( val = parseInt( val, 10 ) ) ) {
        this._content.weeks.val( val );
      } else {
        return parseInt( this._content.weeks.val(), 10 );
      }
    },
    months: function( val ) {
      if ( !isNaN( val = parseInt( val, 10 ) ) ) {
        this._content.months.val( val );
      } else {
        return parseInt( this._content.months.val(), 10 );
      }
    },
    years: function( val ) {
      if ( !isNaN( val = parseInt( val, 10 ) ) ) {
        this._content.years.val( val );
      } else {
        return parseInt( this._content.years.val(), 10 );
      }
    },

    // Returns String in PnYnMnDTnHnMnS format
    // See https://en.wikipedia.org/wiki/ISO_8601#Durations
    getDuration: function() {
      var duration = "P";

      if ( this.options.years && this.options.years.active && this.years() ) {
        duration += this.years() + "Y";
      }

      if ( this.options.months && this.options.months.active && this.months() ) {
        duration += this.months() + "M";
      }

      if ( this.options.days && this.options.days.active && this.days() ) {
        duration += this.days() + "D";
      }

      if ( (this.options.hours && this.options.hours.active) || (this.options.minutes && this.options.minutes.active) || (this.options.seconds && this.options.seconds.active) ) {
        duration += "T";
      }

      if ( this.options.hours && this.options.hours.active && this.hours() ) {
        duration += this.hours() + "H";
      }

      if ( this.options.minutes &&  this.options.minutes.active && this.minutes() ) {
        duration += this.minutes() + "M";
      }

      if ( this.options.seconds && this.options.seconds.active && this.seconds() ) {
        duration += this.seconds() + "S";
      }

      if ( duration[ duration.length - 1 ] === "T" ) {
        duration = duration.substr( 0, duration.length - 1 );
      }

      if (this.options.weeks &&  this.options.weeks.active && this.weeks()) {
        var weeks = this.weeks();
        return duration === "P" ? weeks > 0 ? "P" + weeks + "W": "PT0S" : duration;
      }
      return duration === "P" ? "PT0S" : duration;
    },

    setDuration: function( value ) {
      var formats = [ {

        // PnYnMnDTnHnMnS
        re: /^P((\d+)Y)?((\d+)M)?((\d+)D)?(T((\d+)H)?((\d+)M)?((\d+)S)?)?$/,
        parse: function( value ) {
          var matches = this.re.exec( value );

          for ( var i = 2; i < matches.length; ++i ) {
            matches[ i ] = parseInt( matches[ i ], 10 ) || 0;
          }

          return {
            years: matches[ 2 ],
            months: matches[ 4 ],
            days: matches[ 6 ],
            hours: matches[ 9 ],
            minutes: matches[ 11 ],
            seconds: matches[ 13 ]
          };
        },
        validate: function( value ) {
          return this.re.test( value );
        }
      }, {

        // PnW
        re: /^P(\d+)W$/,
        parse: function( value ) {
          var weeks = this.re.exec( value )[ 1 ];
          return { years: 0, months: 0, weeks: weeks, days: 0, hours: 0, minutes: 0, seconds: 0 };
        },
        validate: function( value ) {
          return this.re.test( value );
        }
      }, {

        // P<date>T<time>
        re: /^P(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})$/,
        parse: function( value ) {
          var date = new Date( value.substr( 1 ) );

          return {
            years: date.getFullYear(),
            months: date.getMonth() + 1,
            weeks: 0,
            days: date.getDate(),
            hours: date.getHours(),
            minutes: date.getMinutes(),
            seconds: date.getSeconds()
          };
        },
        validate: function( value ) {
          return this.re.test( value ) && !isNaN( Date.parse( value.substr( 1 ) ) );
        }
      } ];

      var duration;

      for ( var i = 0; i < formats.length; ++i ) {
        var format = formats[ i ];

        if ( format.validate( value ) ) {
          duration = format.parse( value );
          break;
        }
      }

      if ( !duration ) {
        throw new Error( "Invalid format" );
      }

      if ( this.options.years && this.options.years.active ) {
        this._content.years.val( duration.years );
      }

      if ( this.options.months && this.options.months.active  ) {
        this._content.months.val( duration.months );
      }

      if ( this.options.weeks && this.options.weeks.active  ) {
        this._content.weeks.val( duration.weeks );
      }

      if ( this.options.days && this.options.days.active  ) {
        this._content.days.val( duration.days );
      }

      if ( this.options.hours  && this.options.hours.active ) {
        this._content.hours.val( duration.hours );
      }

      if ( this.options.minutes && this.options.minutes.active  ) {
        this._content.minutes.val( duration.minutes );
      }

      if ( this.options.seconds && this.options.seconds.active  ) {
        this._content.seconds.val( duration.seconds );
      }
    },
    setSeconds: function( value ) {
      value = parseInt( value, 10 );

      if ( isNaN( value ) ) {
        throw new Error( "value is not an integer" );
      }

      var i;
      if ( this.options.years && this.options.years.active ) {
        i = Math.floor( value / YEAR );
        value -= i * YEAR;
        this._content.years.val( i );
      }
      if ( this.options.months && this.options.months.active) {
        i = Math.floor( value / MONTH );
        if ( i >= 12 ) {
          i = 0;
        }
        value -= i * MONTH;
        this._content.months.val( i );
      }
      if ( this.options.weeks && this.options.weeks.active) {
        i = Math.floor( value / WEEK );
        if ( i >= 54 ) { // Max 53 weeks based on ISO 8061 (should start from 1 based on the same ISO)
          i = 0;
        }
        value -= i * WEEK;
        this._content.weeks.val( i );
      }
      if ( this.options.days && this.options.days.active) {
        i = Math.floor( value / DAY );
        if ( i >= 30 ) {
          i = 0;
        }
        value -= i * DAY;
        this._content.days.val( i );
      }
      if ( this.options.hours && this.options.hours.active) {
        i = Math.floor( value / HOUR );
        if ( i >= 24 ) {
          i = 0;
        }
        value -= i * HOUR;
        this._content.hours.val( i );
      }
      if ( this.options.minutes && this.options.minutes.active) {
        i = Math.floor( value / MINUTE );
        if ( i >= 60 ) {
          i = 0;
        }
        value -= i * MINUTE;
        this._content.minutes.val( i );
      }
      if ( this.options.seconds && this.options.seconds.active) {
        i = Math.floor( value );
        if ( i >= 60 ) {
          i = 0;
        }
        this._content.seconds.val( i );
      }
    },
    getSeconds: function() {
      var seconds = 0;
      if ( this.options.seconds && this.options.seconds.active ) {
        seconds += this.seconds();
      }
      if ( this.options.minutes && this.options.minutes.active) {
        seconds += this.minutes() * MINUTE;
      }
      if ( this.options.hours && this.options.hours.active ) {
        seconds += this.hours() * HOUR;
      }
      if ( this.options.days && this.options.days.active ) {
        seconds += this.days() * DAY;
      }
      if ( this.options.weeks && this.options.active ) {
        seconds += this.weeks() * WEEK;
      }
      if ( this.options.months && this.options.months.active ) {
        seconds += this.months() * MONTH;
      }
      if ( this.options.years && this.options.years.active ) {
        seconds += this.years() * YEAR;
      }
      return seconds;
    },
    translate: function() {
      var units = [];
      if ( this.options.years && this.options.years.active && this.years() > 0 ) {
        units.push( this._t( "units.year", this.years() ) );
      }
      if ( this.options.months && this.options.months.active && this.months() > 0 ) {
        units.push( this._t( "units.month", this.months() ) );
      }
      if ( this.options.weeks && this.options.weeks.active && this.weeks() > 0 ) {
        units.push( this._t( "units.week", this.weeks() ) );
      }
      if ( this.options.days && this.options.days.active && this.days() > 0 ) {
        units.push( this._t( "units.day", this.days() ) );
      }
      if ( this.options.hours && this.options.hours.active && this.hours() > 0 ) {
        units.push( this._t( "units.hour", this.hours() ) );
      }
      if ( this.options.minutes && this.options.minutes.active && this.minutes() > 0 ) {
        units.push( this._t( "units.minute", this.minutes() ) );
      }
      if ( this.options.seconds && this.options.seconds.active && this.seconds() > 0 ) {
        units.push( this._t( "units.second", this.seconds() ) );
      }

      var last = "";
      if ( units.length > 1 ) {
        last = " " + this._t( "and" ) + " " + units.pop();
      }
      return units.join( ", " ) + last;
    }
  } );
} )( jQuery );
