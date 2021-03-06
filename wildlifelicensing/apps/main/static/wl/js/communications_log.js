define(['jQuery', 'lodash', 'moment', 'js/wl.dataTable'], function ($, _, moment, dataTable) {
    "use strict";

    // constants
    var DATE_TIME_FORMAT = 'DD/MM/YYYY HH:mm A';

    function initCommunicationLog(options) {
        // default options
        options = _.defaults(options || {}, {
            showLogPopoverSelector: null,
            showLogEntryModalSelector: null,
            logEntryModalSelector: null,
            logEntryFormSelector: null,
            logTableSelector: $('<table id="communicationsLog-table" class="table table-striped table-bordered dataTable">'),
            logListURL: 'insert-default-url-here',
            addLogEntryURL: 'insert-default-url-here'
        });

        // multi-used selectors
        var $logEntryModal = options.logEntryModalSelector ? $(options.logEntryModalSelector): null,
            $logListContent,
            logDataTable;

        // init log entry modal if provided
        if($logEntryModal) {
            $(options.showLogEntryModalSelector).click(function () {
                $logEntryModal.modal('show');
            });
        }

        // if log table is in a popover, need to prepare log table container before initializing table or 
        // search/paging/etc won't show 
        if(options.showLogPopoverSelector) {
            $logListContent = $('<div>').append($(options.logTableSelector));
        }

        // init log table
        logDataTable = initLogTable(options.logListURL, options.logTableSelector);

        // init log table popover if provided
        if(options.showLogPopoverSelector) {
            $(options.showLogPopoverSelector).popover({
                container: 'body',
                title: 'Communication log',
                content: $logListContent,
                placement: 'right',
                trigger: "manual",
                html: true
            }).click(function () {
                var isVisible = $(this).data()['bs.popover'].tip().hasClass('in');

                if (!isVisible) {
                    logDataTable.ajax.reload();
                    $(this).popover('show');
                    $('[data-toggle="tooltip"]').tooltip();
                } else {
                    $(this).popover('hide');
                }
            });
        }

        // init log entry form if provided
        if(options.logEntryFormSelector) {
            $(options.logEntryFormSelector).submit(function (e) {
                var formData, submitPromise;

                e.preventDefault();

                // need a FormData object because it transmits data in the same format as form’s submit() method would,
                // as if the form encoding type were set to “multipart/form-data”, essentially allowing file attachments
                formData = new FormData($(this).get(0));

                submitPromise = $.ajax({
                        url: options.addLogEntryURL,
                        data: formData,
                        contentType: false,
                        processData: false,
                        type: 'POST'
                });

                submitPromise.done(function() {
                    logDataTable.ajax.reload();
                });

                submitPromise.done($.proxy(function() {
                    if($logEntryModal) {
                        $logEntryModal.modal('hide');

                        // clear/reset form fields
                        $(this).find('#id_type').val($('#id_type option:first').val());
                        $(this).find('#id_subject').val('');
                        $(this).find('#id_text').val('');
                        $(this).find('#id_attachment').val('');
                    }},
                    this)
                );
            });
        }
    }

    function initLogTable(logListURL, tableSelector) {
        var $table = $(tableSelector),
            tableOptions = {
                paging: true,
                info: true,
                searching: true,
                processing: true,
                deferRender: true,
                serverSide: false,
                autowidth: true,
                order: [[0, 'desc']],
                ajax: {
                    url: logListURL
                }
            },
            colDefinitions = [
                {
                    title: 'Date',
                    data: 'created',
                    'render': function (date) {
                        return moment(date).format(DATE_TIME_FORMAT);
                    }
                },
                {
                    title: 'Type',
                    data: 'type'
                },
                {
                    title: 'To',
                    data: 'to'
                },
                {
                    title: 'From',
                    data: 'fromm'
                },
                {
                    title: 'Subject/Desc.',
                    data: 'subject'
                },
                {
                    title: 'Text',
                    data: 'text',
                    'render': function (value) {
                        var ellipsis = '...',
                            truncated = _.truncate(value, {
                            length: 100,
                            omission: ellipsis,
                            separator: ' '
                        }),
                            result = '<span>' + truncated +'</span>',
                            popTemplate = _.template('<a href="#" ' +
                                'role="button" ' +
                                'data-toggle="popover" ' +
                                'data-trigger="click" ' +
                                'data-placement="top auto"' +
                                'data-html="true" ' +
                                'data-content="<%= text %>" ' +
                                '>more</a>');
                        if (_.endsWith(truncated, ellipsis)) {
                            result += popTemplate({
                               text: value
                            });
                        }

                        return result;
                    },
                    'createdCell': function (cell) {
                        //TODO why this is not working?
                        // the call to popover is done in the 'draw' event
                        $(cell).popover();
                    }
                },
                {
                    title: 'Document',
                    data: 'document',
                    'render': function (value) {
                        return value ? '<a href="' + value + '" target="_blank"><p>View Document</p></a>': '';
                    }
                }
            ];

        // set DT date format sorting
        dataTable.setDateTimeFormat(DATE_TIME_FORMAT);

        // activate popover when table is drawn.
        $table.on('draw.dt', function () {
            var $tablePopover = $table.find('[data-toggle="popover"]');
            if($tablePopover.length > 0) {
                $tablePopover.popover();
                // the next line prevents from scrolling up to the top after clicking on the popover.
                $($tablePopover).on('click', function(e){
                    e.preventDefault();
                    return true;
                });
            }
        });

        return dataTable.initTable($table, tableOptions, colDefinitions);
    }

    return {
        initCommunicationLog: initCommunicationLog
    };
});