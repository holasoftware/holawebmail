function folder_page_init(data){
    if (data && data.is_empty_folder) return;

    var $searchTextFilterOptions = $("#search_text_filters > .dropdown-item");
    $searchTextFilterOptions.click(function(e){
        e.stopImmediatePropagation();
        var inputCheckbox = $(this).find("> input[type=checkbox]").get(0);
        if (inputCheckbox.checked) {
            inputCheckbox.checked = false;
        } else {
            inputCheckbox.checked = true;
        }
    });

    var $messagelist = $("#messagelist");

    var $messageActionForm = $("#form_message_action");
    $messageActionForm.get(0).reset();

    var $checkAllBtn = $("#check_all");
    var $checkAllInputBox = $checkAllBtn.find("> input[type=checkbox]");

    $checkAllBtn.click(function(){
        $checkAllInputBox.get(0).click();
    });

    $("button.star-btn[data-message-id]").click(function(e){
        e.preventDefault();

        var $this = $(this);
        var $btnIcon = $this.find("> i");

        var isStarred = $this.data("starred") == "1";
        var id = $this.data("message-id");

        if (isStarred){
            var actionUrl = $this.data("unstar-url");

            $.post(actionUrl, {
                url: actionUrl,
                dataType: 'json',
                success: function(data){
                    $this.data("starred", "0");
                    $btnIcon.removeClass("fa-star").addClass("fa-star-o");
                },
                error: function(data){

                }
            })
        } else {
            var actionUrl = $this.data("star-url");
            $.post(actionUrl, {
                url: actionUrl,
                dataType: 'json',
                success: function(data){
                    $this.data("starred", "1");
                    $btnIcon.removeClass("fa-star-o").addClass("fa-star");
                },
                error: function(data){

                }
            })
        }
    });
}
