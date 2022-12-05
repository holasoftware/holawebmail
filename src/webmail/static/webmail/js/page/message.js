function message_page_init(){
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


    var $markAsReadBtn = $("#mark_read");
    var $markAsUnreadBtn = $("#mark_unread");

    $markAsReadBtn.click(function(){
        var actionUrl = $(this).data("url");

        $.post(actionUrl, {
            url: actionUrl,
            dataType: 'json',
            success: function(data){
                $markAsReadBtn.hide();
                $markAsUnreadBtn.show();
            },
            error: function(data){

            }
        })
    });

    $markAsUnreadBtn.click(function(){
        var actionUrl = $(this).data("url");

        $.post(actionUrl, {
            url: actionUrl,
            dataType: 'json',
            success: function(data){
                $markAsReadBtn.show();
                $markAsUnreadBtn.hide();
            },
            error: function(data){

            }
        })
    });

    var $emailContent = $("#email-content");
    var content = $emailContent.text();
    var markedEmailContent = marked(content);
    $emailContent.html(markedEmailContent);
}
