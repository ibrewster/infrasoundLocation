let imageCount=1;

$(document).ready(function(){
    $('#volcs button').click(displayVolc);
    $('#volcs button:first').click();
    $('button.navButton').click(navImages);
    $('button.volcCurrent').click(getImages);
    $('.datetime').datetimepicker({
        format:'m/d/Y H:i',
        mask:true,
        closeOnWithoutClick:true,
        closeOnDateSelect:false,
        defaultSelect:false,
        validateOnBlur:false,
        onClose:closeDebounce
    })


    $(window).resize(function(){
        const count=getImageCount();
        if (count!==imageCount){
            const stopTime=$(document).data('stopTime');
            if(stopTime!==null)
                getImages(stopTime);
            else
                getImages();
        }
    })
})

let endDateTimeVal="";
function closeDebounce(){
    const target=this;
    setTimeout(function(){
        targetDateChanged.call(target);
    }, 100);
}

function targetDateChanged(){
    // All this junk is to PROPERLY handle the
    // closing of the datetimepicker so we
    // don't wind up with infinite loops.
    if( $('.xdsoft_datetimepicker').is(':visible')){
        console.log("Skipping due to not closed")
        return;
    }
    let val=$('.datetime:visible').val();

    // Don't do anything unless the value has actually changed.
    if(val===endDateTimeVal || val=="__/__/____ __:__"){
        console.log("Skipping due to no change");
        return;
    }
    endDateTimeVal=val;

    getImages(val);
}

function displayVolc(){
    $('#volcs button').removeClass('current');
    $(this).addClass('current');

    const volc=$(this).data('volc');
    const dest=$(`#${volc}Tab`);

    $('div.tabDiv').hide();
    dest.show();
    endDateTimeVal="";

    getDetections();
    getImages();
}

function getDetections(){
    const volc=$('#volcs button.current').data('volc');
    $.getJSON(`getDetections/${volc}`)
    .done(function(data){
        let times,values,dist;
        [times,values,dist]=data['detections'];
        color_max=data['max_dist']

        const dest=$('div.volcDetections:visible')[0]
        Plotly.newPlot(
            dest,
            [{
                x:times,
                y:values,
                z:dist,
                mode:"markers",
                marker:{
                    color:dist,
                    cmin:0,
                    cmax:color_max,
                    colorscale:[
                        ['0','rgb(255,0,0)'],
                        ['1.0','rgb(0,0,255)']
                    ],
                    colorbar:{
                        title:{
                            side:"right",
                            text:"Distance to Center (M)"
                        }
                    }
                },
            }],
            {
                margin: {
                    t: 5,
                    b:30,
                    r:0
                },
                xaxis:{
                    tickangle: 0,
                    gridcolor:"rgba(0,0,0,.25)"
                },
                yaxis:{
                    range:[.75,1.075],
                    title:"Stack Amp",
                    gridcolor:"rgba(0,0,0,.25)"
                }
            },
            {responsive: true}
        )

        dest.on('plotly_click',tsClicked);
    })
}

function tsClicked(data){
    const pt=data.points[0];
    $('#endDateTime').val(pt.x).change().blur();
    console.log(pt);
}

function getImageCount(){
    const destDiv=$('div.tabDiv:visible');
    //can use any nav div here, as they should all be the same width
    const navWidth=destDiv.find('div.nav:first').width();
    const viewWidth=$('body').width(); //takes into account any margin
    const count=Math.floor((viewWidth-2*navWidth)/700);
    return count || 1;
}

function getImages(stop_time){
    let url="getImages"
    imageCount=getImageCount(); //update the image count
    let args={"count":imageCount}; //TODO: figure out actual count to send
    const volcButton=$('#volcs button.current')
    const volc=volcButton.data('volc');
    args['volc']=volc;

    if(typeof stop_time !== 'undefined'){
        url="imageBrowse";
        args['stop']=stop_time;
        $(document).data('stopTime',stop_time);
    }
    else{
        $(document).data('stopTime',null);
    }

    $.getJSON(url,args)
    .fail(function(){
        alert(`Unable to fetch images for ${volc}`);
        $(`#${volc}Tab div.infrasoundImages`).empty().html("Unable to retrieve images")
    })
    .done(function(data){
        $(`#${volc}Tab div.nav.prev button`).data('target',data['newest']);
        $(`#${volc}Tab div.nav.next button`).data('target',data['next']);
        if(data['next']===null){
            $(`#${volc}Tab div.nav.next button`).attr('disabled',true);
            $('button.volcCurrent').attr('disabled',true);
        }
        else{
            $(`#${volc}Tab div.nav.next button`).attr('disabled',false);
            $('button.volcCurrent').attr('disabled',false);
        }

        displayImages(data['files'],volc);
    })
}

function displayImages(images,volc){
    const dest=$(`#${volc}Tab div.infrasoundImages`).empty();
    if (images.length==0){
        dest.html("No Images Found");
        return;
    }

    for(var i=images.length-1; i>=0; i--){
        //iterate backwards so oldest to newest
        const imageSet=images[i];
        const setDiv=createImageDiv(imageSet);
        dest.append(setDiv);
    }

}

function createImageDiv(images){
    let div=$('<div class="imageGroup">')
    const imageTypes=['slice','wfs'];
    for(const type of imageTypes ){
        //pull out the images in order

        const img=images.find(function(imageName){
            return imageName.split('.')[0].endsWith(type);
        });

        img_parts=img.split("_");
        img_volc=img_parts[0];
        img_date=img_parts[1];
        img_year=img_date.slice(0,4)
        img_month=img_date.slice(4,6)
        img_day=img_date.slice(6)
        img_path=`${img_volc}/${img_year}/${img_month}/${img_day}/${img}`

        let imgObj=$('<img class=ifsImage>');
        imgObj.prop('src',`getImage/${img_path}`);
        div.append(imgObj);
    }
    return div;
}

function navImages(){
    const target=$(this).data('target');
    if (target>0)
        getImages(target);
    else
        getImages();
}
