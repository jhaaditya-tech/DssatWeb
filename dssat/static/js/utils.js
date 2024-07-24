function generate_charts(){
    var planting_date;
    var daps=[];
    var rate=[];
    var cultivar;
  daps = $('#nitro_dap').val();
  rate=$('#selected_rates').val().split(',');
  planting_date=$('#startDate').val();
  cultivar=$('#cultivar').val();


  console.log(planting_date);
  console.log(cultivar);
  console.log(daps);
  console.log(rate);
  var index = $("#stress_chart_water").data('highchartsChart');
var water_chart= Highcharts.charts[index];
index= $("#stress_chart_nitrogen").data('highchartsChart');
var nitro_chart= Highcharts.charts[index];
index= $("#column_chart").data('highchartsChart');
var column_chart= Highcharts.charts[index];
var series=column_chart.series[0];
console.log(typeof(series.data))
  var json_data={
      'nitrogen_rate':rate,
      'nitrogen_dap':daps,
      'cultivar':cultivar,
      'planting_date':planting_date,
      'dbname':'dssatserv',
      'schema':admin1_country,
      'admin1':admin1,
  }

 var xhr= ajax_call('run-experiment/',json_data);
 xhr.done(function(data){
     var xw=JSON.parse(data.water_series);
      var xn=JSON.parse(data.nitrogen_series);
     water_chart.addSeries(xw,true);
     nitro_chart.addSeries(xn,true);
     // column_chart.addSeries({data:data.yield_series,name:'test'});
     console.log(column_chart.series[0].data);

     $('#selected_rates').val('');
     $('#selected_daps').val('');
    // console.log(JSON.parse(x));
 });


}
function select_chart(btn){
    console.log(btn.id);
    if(btn.id==='yield'){
        document.getElementById('column_chart').style.display='block';
        document.getElementById('anomaly_chart').style.display='none';
    }
    if(btn.id==='anomaly'){
          document.getElementById('column_chart').style.display='none';
        document.getElementById('anomaly_chart').style.display='block';
    }
}
function showVal(val){
        document.getElementById('nitro_rate').innerHTML=val;
}
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
function ajax_call(ajax_url, ajax_data) {
    //update database
    console.log(ajax_data);
    return $.ajax({
        type: "POST",
        headers: {'X-CSRFToken': getCookie('csrftoken')},
        url: ajax_url.replace(/\/?$/, '/'),
        dataType: "json",
        data: ajax_data
    })
        .fail(function (xhr, status, error) {
        });
}
function addToBox(){
   var val= document.getElementById('nitro_rate').innerHTML;
   if( document.getElementById('selected_rates').value.length>0 ){
        document.getElementById('selected_rates').value= document.getElementById('selected_rates').value+','+val;
   }else
   document.getElementById('selected_rates').value=val;
}
