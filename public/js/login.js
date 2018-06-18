$(document).ready(function(){
	$(':text:first').focus();
	$('form').submit(function(e) {
		
		var subButton = $(this).find(':submit')
        subButton.prop('disabled',true)
		$.post("login",$('#mylogin').serialize());
		subButton.val('...sending')
	   });
});