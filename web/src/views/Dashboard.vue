<script setup>
import { useLayout } from '@/layout/composables/layout';
import { onMounted, ref, watch } from 'vue';
import axios from 'axios';

const { getPrimary, getSurface, isDarkTheme } = useLayout();
const APIURL = window.apiUrl


const analysisMetric = ref({});
const termPercentage = ref({});
const tagTotalCount = ref({});
const sentimentPercentages = ref({});
const aspectItemCounts =  ref({});


const pqchartData = ref();
const pqchartOptions = ref();
const pqBarData = ref(null);
const exBarData = ref(null);
const moBarData = ref(null);


const setpqChartData = (data) => {
    const documentStyle = getComputedStyle(document.body);
    return {
        labels: ['Positive', 'Negative'],
        datasets: [
            {
                data: [data.advantages,data.disadvantages],
                backgroundColor: [documentStyle.getPropertyValue('--p-cyan-500'), documentStyle.getPropertyValue('--p-orange-500'), documentStyle.getPropertyValue('--p-gray-500')],
                hoverBackgroundColor: [documentStyle.getPropertyValue('--p-cyan-400'), documentStyle.getPropertyValue('--p-orange-400'), documentStyle.getPropertyValue('--p-gray-400')]
            }
        ]
    };
};



const setpqBarData= (data) => {
    const documentStyle = getComputedStyle(document.documentElement);

    return {
        labels: ["advantages","disadvantages","expectations","motivations"],
        datasets: [
            {
                type: 'bar',
                label: 'Total tags',
                backgroundColor: documentStyle.getPropertyValue('--p-primary-400'),
                data: [data.advantages,data.disadvantages,data.motivations,data.expectations],
                barThickness: 32
            }
        ]
    };
}

const setexBarData= (data) => {
    const documentStyle = getComputedStyle(document.documentElement);

    return {
        labels: data.label,
        datasets: [
            {
                type: 'bar',
                label: 'Tag percentage',
                backgroundColor: documentStyle.getPropertyValue('--p-primary-400'),
                data: data.data,
                barThickness: 32
            }
        ]
    };
}

const setmoBarData= (data) => {
    const documentStyle = getComputedStyle(document.documentElement);

    return {
        labels: data.label,
        datasets: [
            {
                type: 'bar',
                label: 'Tag percentage',
                backgroundColor: documentStyle.getPropertyValue('--p-primary-400'),
                data: data.data,
                barThickness: 32
            }
        ]
    };
}


const setpqChartOptions = () => {
    const documentStyle = getComputedStyle(document.documentElement);
    const textColor = documentStyle.getPropertyValue('--p-text-color');

    return {
        plugins: {
            legend: {
                labels: {
                    usePointStyle: true,
                    color: textColor
                }
            }
        }
    };
};


const chartAreaOptions = {
    indexAxis: 'y'
};


onMounted(() => {
    getMetric()   
});


function getMetric() {
    axios.post(APIURL+'/analysis_metrics',{category_id:localStorage.getItem('dataSetId')}, {
    headers: {
    'Content-Type': 'application/json'
  }})
        .then(response => {
            // console.log("---------获取指标----------")
            // console.log( JSON.parse(response.data.body))
            // 指标统计
            analysisMetric.value = JSON.parse(response.data.body)
            termPercentage.value = JSON.parse(response.data.body).term_percentage
            tagTotalCount.value = JSON.parse(response.data.body).tag_total_count
            sentimentPercentages.value = JSON.parse(response.data.body).sentiment_percentages
            aspectItemCounts.value = JSON.parse(response.data.body).aspect_item_counts
            // 正负标签比
            pqchartData.value = setpqChartData(JSON.parse(response.data.body).tag_total_count)
            pqchartOptions.value = setpqChartOptions()
            // 四类标签数
            pqBarData.value  = setpqBarData(JSON.parse(response.data.body).tag_total_count)
            // 动机
            const exLabel = []
            const exdata = []
            JSON.parse(response.data.body).term_percentage.expectations.forEach(obj => {
                const key = obj[0];
                const value = parseFloat(obj[1].replace('%', ''))

                exLabel.push(key);
                exdata.push(value);
            });
            // console.log(exLabel)
            // console.log(exdata)
            exBarData.value  = setexBarData({
                "label" : exLabel,
                "data" : exdata
            })
            // 期望
            const moLabel = []
            const moData = []
            JSON.parse(response.data.body).term_percentage.expectations.forEach(obj => {
                const key = obj[0];
                const value = parseFloat(obj[1].replace('%', ''))

                moLabel.push(key);
                moData.push(value);
            });
            // console.log(moLabel)
            // console.log(moData)
            moBarData.value  = setmoBarData({
                "label" : moLabel,
                "data" : moData
            })


    })
        .catch(error => {
        console.error(error);
    });
}


</script>

<template>
    <div class="grid grid-cols-12 gap-8">
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">Total number of reviews</span>
                        <div class="text-surface-900 dark:text-surface-0 font-medium text-xl"> {{analysisMetric.review_total_count}} </div>
                    </div>
                    <div class="flex items-center justify-center bg-blue-100 dark:bg-blue-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-shopping-cart text-blue-500 !text-xl"></i>
                    </div>
                </div>
                <span class="text-primary font-medium">{{tagTotalCount.advantages + tagTotalCount.disadvantages + tagTotalCount.motivations + tagTotalCount.expectations }}</span>
                <span class="text-muted-color">Total tags</span>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">Positive tags</span>
                        <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">{{tagTotalCount.advantages }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-orange-100 dark:bg-orange-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-dollar text-orange-500 !text-xl"></i>
                    </div>
                </div>
                <span class="text-primary font-medium">{{ parseFloat( tagTotalCount.advantages / (tagTotalCount.advantages + tagTotalCount.disadvantages + tagTotalCount.motivations + tagTotalCount.expectations)*100 ).toFixed(2)}} %</span>
                <span class="text-muted-color">Tag percentage</span>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">Purchase motivation</span>
                        <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">{{tagTotalCount.motivations }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-cyan-100 dark:bg-cyan-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-users text-cyan-500 !text-xl"></i>
                    </div>
                </div>
                <span class="text-primary font-medium">{{ parseFloat( tagTotalCount.motivations / (tagTotalCount.advantages + tagTotalCount.disadvantages + tagTotalCount.motivations + tagTotalCount.expectations) *100 ).toFixed(2)}} % </span>
                <span class="text-muted-color">Tag percentage</span>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">Expectations</span>
                        <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">{{tagTotalCount.expectations }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-purple-100 dark:bg-purple-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-comment text-purple-500 !text-xl"></i>
                    </div>
                </div>
                <span class="text-primary font-medium">{{ parseFloat( tagTotalCount.expectations / (tagTotalCount.advantages + tagTotalCount.disadvantages + tagTotalCount.motivations + tagTotalCount.expectations)*100 ).toFixed(2)}} % </span>
                <span class="text-muted-color">Tag percentage</span>
            </div>
        </div>
        

        <div class="col-span-12 xl:col-span-6">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Positive and negative review percentage</div>
                <Chart type="pie" :data="pqchartData" :options="pqchartOptions" class="w-full md:w-[25rem]" />
            </div>
        </div>
        <div class="col-span-12 xl:col-span-6">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Number of advantages, disadvantages, expectations, and motivations</div>
                <Chart type="bar" :data="pqBarData" :options="pqchartOptions" />
                
            </div>
        </div>


        <div class="col-span-12 xl:col-span-6">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Positive reviews</div>
                <DataTable :value="termPercentage.advantages" :rows="8" :paginator="true" responsiveLayout="scroll">
                
                    <Column field="0" header="Tag" style="width: 65%"></Column>
                    <Column field="1" header="Percentage" :sortable="true" style="width: 35%"></Column>
                   
                </DataTable>
            </div>

           

            <div class="card">
                <div class="flex justify-between items-center mb-6">
                    <div class="font-semibold text-xl">Negative reviews</div>
                </div>
                <ul class="list-none p-0 m-0" style="overflow-y: scroll;height: 480px;"> 
                    <li class="flex flex-col md:flex-row md:items-center md:justify-between mb-6" v-for="item in termPercentage.disadvantages" :key="item.id">
                        <div>
                            <span class="text-surface-900 dark:text-surface-0 font-medium mr-2 mb-1 md:mb-0">{{item[0]}}</span>
                            <div class="mt-1 text-muted-color"> </div>
                        </div>
                        <div class="mt-2 md:mt-0 flex items-center">
                            <div class="bg-surface-300 dark:bg-surface-500 rounded-border overflow-hidden w-40 lg:w-24" style="height: 8px">
                                <div class="bg-orange-500 h-full" :style="{width: item[1] + '%'}"></div>
                            </div>
                            <span class="text-orange-500 ml-4 font-medium">%{{ parseFloat(item[1]).toFixed(2) }}  </span>
                        </div>
                    </li>
                    
                </ul>
            </div>
        </div>


        <div class="col-span-12 xl:col-span-6">
            <div class="card">
                <div class="font-semibold text-xl mb-4">Purchase motivation</div>
                <Chart type="bar" :data="moBarData" :options="pqchartOptions" class="h-80" />
            </div>

            <div class="card">
                <div class="font-semibold text-xl mb-4">Expectations</div>
                <Chart type="bar" :data="exBarData" :options="chartAreaOptions" class="h-[30rem]"  :indexAxis="y" />
            

            </div>
           
        </div>
    </div>
</template>
