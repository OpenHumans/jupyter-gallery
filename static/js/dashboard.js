$(document).ready(function(){
    $("#previewModal").on('show.bs.modal', function (e) {
      var nbid = $(e.relatedTarget).data('nbid');
      var nbtitle = $(e.relatedTarget).data('nbtitle');
      console.log(nbtitle);
      console.log($('#nbtitle_fill').html);
      $('#notebook_filler').load('/render-notebook/'+nbid);
      $('#nbtitle_fill').html(nbtitle);
      $('#nbopenId').attr("href", '/open-notebook/'+nbid);
      $('#detailId').attr("href", '/notebook/'+nbid);
      //document.getElementById("notebook_filler").innerHTML = "new content"
        ///alert('The modal will show'+nbid);
    });
    $('[data-toggle="tooltip"]').tooltip();
});
