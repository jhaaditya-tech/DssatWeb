
function get_daps(){
    var daps=[];
    let tbl = document.getElementById("nitrogen_table").getElementsByTagName('tbody')[0];
    for(var i=0;i<tbl.rows.length;i++) {
        daps.push(tbl.rows[i].cells[0].innerText);
    }
return daps;
}
function get_rates(){
  var rates=[];
    let tbl = document.getElementById("nitrogen_table").getElementsByTagName('tbody')[0];
    for(var i=0;i<tbl.rows.length;i++) {


        rates.push(tbl.rows[i].cells[1].innerText);
    }
return rates;
}
function generate_charts(){
    var planting_date;
    var daps=[];
    var rate=[];
    var cultivar;
  daps = get_daps();
  rate=get_rates();
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
// index= $("#column_chart").data('highchartsChart');
// var column_chart= Highcharts.charts[index];
// var series=column_chart.series[0];
// console.log(typeof(series.data))
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
     // var xw=JSON.parse(data.water_series);
     //  var xn=JSON.parse(data.nitrogen_series);
     // water_chart.addSeries(xw,true);
     // nitro_chart.addSeries(xn,true);
     // column_chart.addSeries({data:data.yield_series,name:'test'});
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
// function showVal_dap(val){
//         document.getElementById('nitro_dap').innerHTML=val;
// }
// function showVal_rate(val){
//         document.getElementById('nitro_rate').innerHTML=val;
// }
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
   var val_rate= document.getElementById('customRange2').value;
   var val_dap= document.getElementById('customRange1').value;
   if (val_dap && val_rate) {
       var tbodyRef = document.getElementById('nitrogen_table').getElementsByTagName('tbody')[0];

// Insert a row at the end of table
       var newRow = tbodyRef.insertRow();

// Insert a cell at the end of the row
       var newCell = newRow.insertCell();

// Append a text node to the cell
       var newText = document.createTextNode(val_dap);
       newCell.appendChild(newText);

       newCell = newRow.insertCell();

// Append a text node to the cell
       newText = document.createTextNode(val_rate);
       newCell.appendChild(newText);
       newCell = newRow.insertCell();
       newText = document.createTextNode('Delete');
       newCell.appendChild(newText);
   }
   else {
       alert('please enter values')
   }

}

