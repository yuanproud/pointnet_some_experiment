data = h5read('ply_data_train0.h5', '/data');
data_sum = sum(data);
data_reshape = reshape(data_sum, [1, 1, 2048*2048]);
for i = 1:2048*2048-1
    for j = 1:2048*2048-1
        if(data_reshape(1,1,j) > data_reshape(1,1,j+1))
            c = data_reshape(1,1,j);
            data_reshape(1,1,j) = data_reshape(1,1,j+1);
            data_reshape(1,1,j+1) = c;
        end
    end
end
    