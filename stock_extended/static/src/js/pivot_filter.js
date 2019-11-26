odoo.define('stock_extended.pivot_filter', function(require) {
    "use strict";

    var field_utils = require('web.field_utils');
    var PivotRenderer = require('web.PivotRenderer');
    var PivotController = require('web.PivotController');

    PivotRenderer.include({
        _renderRows: function ($tbody, rows) {
            var self = this;
            var open_product_move_filter_view = (self.state.context.open_product_move_filter_view  == 1 )? true : false;
            if(open_product_move_filter_view){
                var i, j, value, measure, name, formatter, $row, $cell, $header;
                var nbrMeasures = this.state.measures.length;
                var length = rows[0].values.length;
                var shouldDisplayTotal = this.state.mainColWidth > 1;

                var groupbyLabels = _.map(this.state.rowGroupBys, function (gb) {
                    return self.state.fields[gb.split(':')[0]].string;
                });
                var measureTypes = this.state.measures.map(function (name) {
                    var type = self.state.fields[name].type;
                    return type === 'many2one' ? 'integer' : type;
                });
                for (i = 0; i < rows.length; i++) {
                    $row = $('<tr>');
                    $header = $('<td>')
                        .text(rows[i].title)
                        .data('id', rows[i].id)
                        .css('padding-left', (5 + rows[i].indent * 30) + 'px')
                        .addClass(rows[i].expanded ? 'o_pivot_header_cell_opened' : 'o_pivot_header_cell_closed');
                    if (rows[i].indent > 0) $header.attr('title', groupbyLabels[rows[i].indent - 1]);
                    $header.appendTo($row);
                    for (j = 0; j < length; j++) {
                        value = rows[i].values[j];
                        name = this.state.measures[j % nbrMeasures];
                        if(name == 'qty_done'){
                            value = value- rows[i].values[j+1];
                        }
                        formatter = field_utils.format[this.fieldWidgets[name] || measureTypes[j % nbrMeasures]];
                        measure = this.state.fields[name];
                        if (this.compare) {
                            if (value instanceof Object) {
                                for (var origin in value) {
                                    $cell = $('<td>')
                                        .data('id', rows[i].id)
                                        .data('measure',name)
                                        .data('col_id', rows[i].col_ids[Math.floor(j / nbrMeasures)])
                                        .data('type' , origin)
                                        .toggleClass('o_empty', false)
                                        .addClass('o_pivot_cell_value text-right');
                                    if (origin === 'data') {
                                        $cell.append($('<div>', {class: 'o_value'}).html(formatter(
                                            value[origin],
                                            measure
                                        )));
                                    } else if (origin === 'comparisonData') {
                                        $cell.append($('<div>', {class: 'o_comparison_value'}).html(formatter(
                                            value[origin],
                                            measure
                                        )));
                                    } else {
                                        $cell.append($('<div>', {class: 'o_variation' + value[origin].signClass}).html(
                                            field_utils.format.percentage(
                                                value[origin].magnitude,
                                                measure
                                            )
                                        ));
                                    }
                                    if (((j >= length - this.state.measures.length) && shouldDisplayTotal) || i === 0){
                                        $cell.css('font-weight', 'bold');
                                    }
                                    $cell.toggleClass('d-none d-md-table-cell', j < length - nbrMeasures);
                                    $row.append($cell);
                                }
                            } else {
                                for (var l=0; l < 3; l++) {
                                    $cell = $('<td>')
                                        .data('id', rows[i].id)
                                        .data('measure',name)
                                        .toggleClass('o_empty', true)
                                        .addClass('o_pivot_cell_value text-right');
                                    $row.append($cell);
                                }
                            }
                        } else {
                            $cell = $('<td>')
                                        .data('id', rows[i].id)
                                        .data('measure',name)
                                        .data('col_id', rows[i].col_ids[Math.floor(j / nbrMeasures)])
                                        .toggleClass('o_empty', !value)
                                        .addClass('o_pivot_cell_value text-right');
                            if (value !== undefined) {
                                $cell.append($('<div>', {class: 'o_value'}).html(formatter(value, measure)));
                            }
                            if (((j >= length - this.state.measures.length) && shouldDisplayTotal) || i === 0){
                                $cell.css('font-weight', 'bold');
                            }
                            $row.append($cell);

                            $cell.toggleClass('d-none d-md-table-cell', j < length - nbrMeasures);
                        }
                    }
                    $tbody.append($row);
                }
            }else{
                this._super($tbody, rows)
            }
            
        },
    });

    PivotController.include({
        _onCellClick: function (event) {
            var $target = $(event.currentTarget);
            if ($target.hasClass('o_pivot_header_cell_closed') ||
                $target.hasClass('o_pivot_header_cell_opened') ||
                $target.hasClass('o_empty') ||
                $target.data('type') === 'variation' ||
                !this.enableLinking) {
                return;
            }
            var state = this.model.get(this.handle);
            var colDomain, rowDomain;
            if ($target.data('type') === 'comparisonData') {
                colDomain = this.model.getHeader($target.data('col_id')).comparisonDomain || [];
                rowDomain = this.model.getHeader($target.data('id')).comparisonDomain || [];
            } else {
                colDomain = this.model.getHeader($target.data('col_id')).domain || [];
                rowDomain = this.model.getHeader($target.data('id')).domain || [];
            }
            var context = _.omit(state.context, function (val, key) {
                return key === 'group_by' || _.str.startsWith(key, 'search_default_');
            });
            var open_product_move_filter_view = (context.open_product_move_filter_view == 1) ? true : false;
            if(open_product_move_filter_view && $target.data('measure') == 'return_qty'){
                var dest = JSON.stringify(["location_dest_id", "ilike", "Partner Locations/Customers"])
                rowDomain = _.reject(rowDomain,function(num){return JSON.stringify(num) == dest;})
                colDomain = _.reject(colDomain,function(num){return JSON.stringify(num) == dest;})
                rowDomain = _.reject(rowDomain,function(num){return num == '|';})
                colDomain = _.reject(colDomain,function(num){return num == '|';})
            }else if(open_product_move_filter_view && $target.data('measure') == 'qty_done'){
                var dest = JSON.stringify(["location_id", "ilike", "Partner Locations/Customers"])
                rowDomain = _.reject(rowDomain,function(num){return JSON.stringify(num) == dest;})
                colDomain = _.reject(colDomain,function(num){return JSON.stringify(num) == dest;})
                rowDomain = _.reject(rowDomain,function(num){return num == '|';})
                colDomain = _.reject(colDomain,function(num){return num == '|';})
            }
            this.do_action({
                type: 'ir.actions.act_window',
                name: this.title,
                res_model: this.modelName,
                views: this.views,
                view_type: 'list',
                view_mode: 'list',
                target: 'current',
                context: context,
                domain: state.domain.concat(rowDomain, colDomain),
            });
        },
    });

});
