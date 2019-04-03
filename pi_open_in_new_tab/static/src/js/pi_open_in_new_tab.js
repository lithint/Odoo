odoo.define('open_in_new_tab.new_tab', function(require) {
"use strict";
var core = require('web.core');
var Widget = require('web.Widget');
var BasicRenderer = require('web.BasicRenderer');
var ActionManager = require('web.ActionManager');
var ListRenderer = require('web.ListRenderer');
var ActionManager = require('web.ActionManager');
var ListController = require('web.ListController');
var AbstractController = require('web.AbstractController');
var core = require('web.core');
var Dialog = require('web.Dialog');
//var pyeval = require('web.pyeval');
var Sidebar = require('web.Sidebar');
var _t = core._t;
var qweb = core.qweb;

var tab_limit = 8;

AbstractController.include({            // Trigger up function for new tab

     init: function (parent, model, renderer, params) {
        this.custom_events['open_in_new_tab'] = "_open_in_new_tab";
        this._super.apply(this, arguments);
        this.action_manager = parent;
    },

    _open_in_new_tab: function (event) {
        event.stopPropagation();
        var record = this.model.get(event.data.id, {raw: true});
        var getUrl = window.location;
        var baseUrl = getUrl .protocol + "//" + getUrl.host + "/" + getUrl.pathname.split('/')[1];
        var model_name = record.model;
        var action_id = '';
        if(this.importEnabled){
            this.action_manager.do_action({ type: 'ir.actions.act_url',
                url:baseUrl+'#id='+record.res_id+'&view_type=form&model='+model_name+'&action='+action_id,
                target: 'new'
             });
        }else{
              this.action_manager.do_action({ type: 'ir.actions.act_url',
              url:baseUrl+'#id='+record.res_id+'&view_type=form&model='+model_name, //+'&action='+action_id,
              target: 'new'
             });

        };

    },
});

ListRenderer.include({              // Add the icon and th and fooder
    _renderHeader: function (isGrouped) {          //over ride the base funcions
        // Todo : Get the tr element and append <th>

        var $tr = $('<tr>').append(_.map(this.columns, this._renderHeaderCell.bind(this)));
      if (this.hasSelectors) {
            $tr.prepend(this._renderSelector('th'));
            $tr.append($('<th>').html('&nbsp;'));
       }else{
            var $tr = $('<tr>').append(_.map(this.columns, this._renderHeaderCell.bind(this)));
            $tr.append($('<th>').html('&nbsp;'));
       }
       return $('<thead>').append($tr);
    },

//       if (isGrouped) {
//            $tr.prepend($('<th>').html('&nbsp;'));
//        }

    _renderFooter: function (isGrouped) {
        var aggregates = {};
        _.each(this.columns, function (column) {
            if ('aggregate' in column) {
                aggregates[column.attrs.name] = column.aggregate;
            }
        });
        var $cells = this._renderAggregateCells(aggregates);
        if (isGrouped) {
            $cells.unshift($('<td>'));
        }
        if (this.hasSelectors) {
            $cells.unshift($('<td>'));
        }
        return $('<tfoot>').append($('<tr>').append($cells).append("<td>"));
    },

    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
           $row.append('<td class="fa fa-external-link" id="new_tab" />');
        return $row;
    },
    _onRowClicked: function (event) {
//        var getUrl = window.location;
//        var baseUrl = getUrl .protocol + "//" + getUrl.host + "/" + getUrl.pathname.split('/')[1];

//        var record_id = this.state.context.params.id;
//        var model_name = this.state.context.params.model;
//        var action_id = this.state.context.params.action;
//        var menu_id = this.state.context.params.menu_id;
        if (!this._isEditable()) {
            var currentTargetId = $(event.target).attr("id");
            if(currentTargetId == 'new_tab'){
                var id = $(event.currentTarget).data('id');
                if (id) {
                    this.trigger_up('open_in_new_tab', {id:id, target: event.target});
                }
            }else{
                if (!$(event.target).prop('special_click')) {
                    var id = $(event.currentTarget).data('id');
                    if (id) {
                        this.trigger_up('open_record', {id:id, target: event.target});
                    }
                }
            }
        }
    },
});

ListController.include({                // Add the menu in side bar in icon

    init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
    },

 // Todo : include the side bar instead of overriding function
    renderSidebar: function ($node) {
        var self = this;
        if (this.hasSidebar && !this.sidebar) {
            var other = [{
                label: _t("Export"),
                callback: this._onExportData.bind(this)
            }];

            other.push({
                    label: _t("Open in New Tab"),
                    callback: this._open_new_tab.bind(this, true)
                });

            if (this.archiveEnabled) {
                other.push({
                    label: _t("Archive"),
                    callback: function () {
                        Dialog.confirm(self, _t("Are you sure that you want to archive all the selected records?"), {
                            confirm_callback: self._onToggleArchiveState.bind(self, true),
                        });
                    }
                });
                other.push({
                    label: _t("Unarchive"),
                    callback: this._onToggleArchiveState.bind(this, false)
                });
            }
            if (this.is_action_enabled('delete')) {
                other.push({
                    label: _t('Delete'),
                    callback: this._onDeleteSelectedRecords.bind(this)
                });
            }
            this.sidebar = new Sidebar(this, {
                editable: this.is_action_enabled('edit'),
                env: {
                    context: this.model.get(this.handle, {raw: true}).getContext(),
                    activeIds: this.getSelectedIds(),
                    model: this.modelName,
                },
                actions: _.extend(this.toolbarActions, {other: other}),
            });
            this.sidebar.appendTo($node);

            this._toggleSidebar();
        }
    },

    _open_new_tab: function () {
         var link_array = Array();
         var ids =this.getSelectedIds();
         var record = this.model.get(this.handle);
         // var model= this.modelName;
         var model = record.model;
         var action_id = '';
         var tab_arr = "";
         for (var a in ids   ) {
                var getUrl = window.location;
                var baseUrl = getUrl .protocol + "//" + getUrl.host + "/" + getUrl.pathname.split('/')[1];
                var url = baseUrl+'#id='+ids[a]+'&view_type=form&model='+model+'&action='+action_id;
                link_array.push(url);
                tab_arr += "window.open('" + url +"', '_blank');";
        }
        if(link_array.length <= tab_limit ){    // Check tabs more than 8
            eval(tab_arr + "");
        }else{
            this.do_warn(_t(" Maximum 8 records  are allowed."))
        }
    },
});
});

